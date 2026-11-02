"""Application service: display→VRAM/RAM helpers over the Debugger port."""
from ..domain.display import (
    BgCell,
    BgLayer,
    ObjTileMapping,
    ScreenCell,
    rgb555,
    tile_indices,
)
from ..domain.io import IoMap
from .ports import Debugger
from io import BytesIO

from PIL import Image
from .video import VideoReader

_MAX_RAM = 0x400000


class DisplayReader:
    """Service: resolve BG cells, read tiles and find tiles in RAM."""

    def __init__(self, debugger: Debugger, io_map: IoMap) -> None:
        """Build the service."""
        self._debugger = debugger
        self._video = VideoReader(debugger, io_map)

    def _bg_layer(self, engine: str, bg: int) -> BgLayer:
        key = engine.upper()
        state = self._video.state(key)
        hofs = state.scrolls[bg][0].raw if state.scrolls else 0
        vofs = state.scrolls[bg][1].raw if state.scrolls else 0
        return BgLayer.from_registers(
            key, bg, state.dispcnt.raw, state.bgs[bg].raw, hofs, vofs
        )

    def map_cell(self, engine: str, bg: int, x: int, y: int) -> BgCell:
        """Resolve a BG cell to its map entry, tile index/address and palette."""
        layer = self._bg_layer(engine, bg)
        info = layer.cell(x, y)
        size = 2 if info.kind == "text" else 1
        entry = int.from_bytes(self._debugger.read_memory(info.entry_addr, size), "little")
        return layer.decode(info, entry)

    def cell_at_screen(
        self, engine: str, bg: int, x: int, y: int
    ) -> tuple[ScreenCell, BgCell]:
        """Resolve a screen pixel to the BG cell (text BG, with scroll)."""
        layer = self._bg_layer(engine, bg)
        screen = layer.cell_from_screen(x, y)
        info = screen.info
        size = 2 if info.kind == "text" else 1
        entry = int.from_bytes(
            self._debugger.read_memory(info.entry_addr, size), "little"
        )
        return screen, layer.decode(info, entry)

    def dump_bg_map(
        self, engine: str, bg: int
    ) -> tuple[dict, list[dict]]:
        """Dump the full virtual BG map (text or affine) as cells.

        Parameters:
            engine (str): ``A`` or ``B``.
            bg (int): BG layer 0..3.

        Returns:
            tuple[dict, list[dict]]: Map metadata and one entry per cell.

        Raises:
            ValueError: If the BG kind is not text/affine.
        """
        layer = self._bg_layer(engine, bg)
        if layer.kind not in ("text", "affine"):
            raise ValueError(
                f"BG {bg} é {layer.kind}; dump_bg_map suporta text/affine nesta versão"
            )
        width, height = layer.map_size
        cell_w, cell_h = width // 8, height // 8
        entry_size = 2 if layer.kind == "text" else 1
        map_data = self._debugger.read_memory(
            layer.screen_base, cell_w * cell_h * entry_size
        )
        cells: list[dict] = []
        for cy in range(cell_h):
            for cx in range(cell_w):
                info = layer.cell(cx * 8, cy * 8)
                offset = info.entry_addr - layer.screen_base
                entry = int.from_bytes(
                    map_data[offset:offset + entry_size], "little"
                )
                cell = layer.decode(info, entry)
                cells.append(
                    {
                        "cell_x": cx,
                        "cell_y": cy,
                        "entry": entry,
                        "tile_index": cell.tile_index,
                        "tile_addr": cell.tile_addr,
                        "palette": cell.palette,
                        "flip_h": cell.flip_h,
                        "flip_v": cell.flip_v,
                    }
                )
        meta = {
            "engine": layer.engine,
            "bg": layer.bg,
            "kind": layer.kind,
            "bpp": layer.bpp,
            "width": width,
            "height": height,
            "cell_count": len(cells),
            "screen_base": layer.screen_base,
            "char_base": layer.char_base,
            "palette_base": layer.palette_base,
        }
        return meta, cells

    def render_bg_map(
        self, engine: str, bg: int
    ) -> tuple[bytes, dict]:
        """Compose the full virtual BG map into a transparent PNG.

        Parameters:
            engine (str): ``A`` or ``B``.
            bg (int): BG layer 0..3.

        Returns:
            tuple[bytes, dict]: PNG bytes and map metadata.

        Raises:
            ValueError: If the BG kind is not text/affine.
        """
        meta, cells = self.dump_bg_map(engine, bg)
        bpp = meta["bpp"]
        tile_size = 64 if bpp == 8 else 32
        max_tile = max((cell["tile_index"] for cell in cells), default=0)
        tile_data = self._debugger.read_memory(
            meta["char_base"], (max_tile + 1) * tile_size
        )
        palette_data = self._debugger.read_memory(meta["palette_base"], 512)
        palette = [
            rgb555(int.from_bytes(palette_data[i * 2:i * 2 + 2], "little"))
            for i in range(256)
        ]
        image = Image.new("RGBA", (meta["width"], meta["height"]), (0, 0, 0, 0))
        pixels = image.load()
        assert pixels is not None
        for cell in cells:
            offset = cell["tile_index"] * tile_size
            tile = tile_data[offset:offset + tile_size]
            if len(tile) < tile_size:
                continue
            rows = tile_indices(tile, bpp)
            base_x = cell["cell_x"] * 8
            base_y = cell["cell_y"] * 8
            palette_index = cell["palette"] if bpp == 4 else None
            for y in range(8):
                for x in range(8):
                    sx = 7 - x if cell["flip_h"] else x
                    sy = 7 - y if cell["flip_v"] else y
                    index = rows[sy][sx]
                    if index == 0:
                        pixels[base_x + x, base_y + y] = (0, 0, 0, 0)
                        continue
                    color_index = (
                        (palette_index or 0) * 16 + index
                        if bpp == 4
                        else index
                    )
                    red, green, blue = palette[color_index % 256]
                    pixels[base_x + x, base_y + y] = (red, green, blue, 255)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue(), meta

    def tile_bytes(
        self,
        engine: str,
        tile_index: int,
        layer: str = "bg",
        bg: int = 0,
        bpp: int | None = None,
    ) -> tuple[int, int, bytes]:
        """Return ``(tile_addr, bpp, bytes)`` for a BG or OBJ tile."""
        key = engine.upper()
        if layer == "bg":
            bg_layer = self._bg_layer(key, bg)
            depth = bg_layer.bpp
            addr = bg_layer.char_base + tile_index * (64 if depth == 8 else 32)
        elif layer == "obj":
            depth = bpp if bpp is not None else 4
            if depth not in (4, 8):
                raise ValueError("bpp deve ser 4 ou 8")
            state = self._video.state(key)
            addr = ObjTileMapping.from_registers(key, state.dispcnt.raw).address(
                tile_index, depth
            )
        else:
            raise ValueError("layer deve ser 'bg' ou 'obj'")
        size = 64 if depth == 8 else 32
        return addr, depth, self._debugger.read_memory(addr, size)

    def find_tile_in_ram(
        self,
        engine: str,
        tile_index: int,
        layer: str = "bg",
        bg: int = 0,
        bpp: int | None = None,
        ram_addr: int = 0x02000000,
        ram_size: int = _MAX_RAM,
        limit: int = 32,
    ) -> tuple[int, int, list[int]]:
        """Find a tile's bytes in RAM; returns ``(tile_addr, bpp, addresses)``."""
        ram_size = max(1, min(ram_size, _MAX_RAM))
        tile_addr, depth, pattern = self.tile_bytes(engine, tile_index, layer, bg, bpp)
        data = self._debugger.read_memory(ram_addr, ram_size)
        found: list[int] = []
        start = 0
        while len(found) < limit:
            index = data.find(pattern, start)
            if index < 0:
                break
            found.append(ram_addr + index)
            start = index + 1
        return tile_addr, depth, found
