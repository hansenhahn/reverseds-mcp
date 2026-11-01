"""Application service: display→VRAM/RAM helpers over the Debugger port."""
from ..domain.display import BgCell, BgLayer, ObjTileMapping
from ..domain.io import IoMap
from .ports import Debugger
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
        return BgLayer.from_registers(key, bg, state.dispcnt.raw, state.bgs[bg].raw)

    def map_cell(self, engine: str, bg: int, x: int, y: int) -> BgCell:
        """Resolve a BG cell to its map entry, tile index/address and palette."""
        layer = self._bg_layer(engine, bg)
        info = layer.cell(x, y)
        size = 2 if info.kind == "text" else 1
        entry = int.from_bytes(self._debugger.read_memory(info.entry_addr, size), "little")
        return layer.decode(info, entry)

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
