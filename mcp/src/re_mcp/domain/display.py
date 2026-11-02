"""BG/OBJ display model: layers, map cells and tile addresses (pure)."""
from dataclasses import dataclass

_TEXT_SIZES = ((256, 256), (512, 256), (256, 512), (512, 512))
_AFFINE_SIZES = ((128, 128), (256, 256), (512, 512), (1024, 1024))
_ENGINE_BG_BASE = {"A": 0x06000000, "B": 0x06200000}
_ENGINE_OBJ_BASE = {"A": 0x06400000, "B": 0x06600000}
_ENGINE_PALETTE_BASE = {"A": 0x05000000, "B": 0x05000400}


def tile_indices(data: bytes, bpp: int) -> tuple[tuple[int, ...], ...]:
    """Decode an 8×8 tile into palette indices.

    Parameters:
        data (bytes): 32 bytes (4bpp) or 64 bytes (8bpp).
        bpp (int): 4 or 8.

    Returns:
        tuple[tuple[int, ...], ...]: Eight rows of eight indices.

    Raises:
        ValueError: If ``bpp`` is invalid or the data is too short.
    """
    if bpp == 4:
        if len(data) < 32:
            raise ValueError("tile 4bpp precisa de 32 bytes")
        rows = []
        for y in range(8):
            row = []
            for x in range(8):
                byte = data[y * 4 + x // 2]
                row.append((byte >> 4) if x & 1 else (byte & 0x0F))
            rows.append(tuple(row))
        return tuple(rows)
    if bpp == 8:
        if len(data) < 64:
            raise ValueError("tile 8bpp precisa de 64 bytes")
        return tuple(
            tuple(data[y * 8 + x] for x in range(8)) for y in range(8)
        )
    raise ValueError("bpp deve ser 4 ou 8")


def rgb555(value: int) -> tuple[int, int, int]:
    """Convert a 15-bit BGR555 colour to 8-bit RGB."""
    red = value & 0x1F
    green = (value >> 5) & 0x1F
    blue = (value >> 10) & 0x1F
    return (
        (red << 3) | (red >> 2),
        (green << 3) | (green >> 2),
        (blue << 3) | (blue >> 2),
    )


@dataclass(frozen=True, slots=True)
class BgCellInfo:
    """Where a BG cell's map entry lives and the layer parameters."""

    engine: str
    bg: int
    kind: str
    x: int
    y: int
    cell_x: int
    cell_y: int
    entry_addr: int
    char_base: int
    screen_base: int
    map_width: int
    map_height: int
    bpp: int


@dataclass(frozen=True, slots=True)
class ScreenCell:
    """A screen pixel's BG cell, including map coordinates and the scroll used."""

    info: BgCellInfo
    screen_x: int
    screen_y: int
    screen_cell_x: int
    screen_cell_y: int
    screen_rect: tuple[int, int, int, int]
    map_x: int
    map_y: int
    hofs: int
    vofs: int


@dataclass(frozen=True, slots=True)
class BgCell:
    """A decoded BG map cell."""

    engine: str
    bg: int
    kind: str
    x: int
    y: int
    cell_x: int
    cell_y: int
    entry_addr: int
    entry: int
    tile_index: int
    tile_addr: int
    palette: int | None
    bpp: int
    flip_h: bool
    flip_v: bool
    char_base: int
    screen_base: int
    map_width: int
    map_height: int


@dataclass(frozen=True, slots=True)
class BgLayer:
    """A BG layer: its raw registers and the behavior to resolve/decode cells."""

    engine: str
    bg: int
    dispcnt: int
    bgcnt: int
    hofs: int = 0
    vofs: int = 0

    @classmethod
    def from_registers(
        cls,
        engine: str,
        bg: int,
        dispcnt: int,
        bgcnt: int,
        hofs: int = 0,
        vofs: int = 0,
    ) -> "BgLayer":
        """Build a layer from the raw DISPCNT/BGxCNT/scroll values."""
        key = engine.upper()
        if key not in ("A", "B"):
            raise ValueError("engine deve ser 'A' ou 'B'")
        if not 0 <= bg <= 3:
            raise ValueError("bg deve ser 0..3")
        return cls(key, bg, dispcnt, bgcnt, hofs, vofs)

    @property
    def kind(self) -> str:
        """Return the layer kind (text/affine/extended/3d/large/invalid)."""
        mode = self.dispcnt & 0x7
        if mode == 6:
            if self.engine == "A" and self.bg == 0:
                return "3d"
            return "large" if self.bg == 2 else "invalid"
        if self.engine == "A" and self.bg == 0 and (self.dispcnt & (1 << 3)):
            return "3d"
        if mode == 0:
            return "text"
        if mode == 1:
            return "affine" if self.bg == 2 else "text"
        if mode == 2:
            return "affine" if self.bg in (2, 3) else "text"
        if mode == 3:
            return "extended" if self.bg == 3 else "text"
        if mode == 4:
            return "affine" if self.bg == 2 else ("extended" if self.bg == 3 else "text")
        if mode == 5:
            return "extended" if self.bg in (2, 3) else "text"
        return "invalid"

    @property
    def map_size(self) -> tuple[int, int]:
        """Return the map size in pixels."""
        size = (self.bgcnt >> 14) & 0x3
        table = _AFFINE_SIZES if self.kind == "affine" else _TEXT_SIZES
        return table[size]

    @property
    def char_base(self) -> int:
        """Return the absolute character base address."""
        value = ((self.bgcnt >> 2) & 0x3) * 0x4000
        if self.engine == "A":
            value += ((self.dispcnt >> 24) & 0x7) * 0x10000
        return _ENGINE_BG_BASE[self.engine] + value

    @property
    def screen_base(self) -> int:
        """Return the absolute screen (map) base address."""
        value = ((self.bgcnt >> 8) & 0x1F) * 0x800
        if self.engine == "A":
            value += ((self.dispcnt >> 27) & 0x7) * 0x10000
        return _ENGINE_BG_BASE[self.engine] + value

    @property
    def bpp(self) -> int:
        """Return the bit depth (affine is always 8bpp)."""
        if self.kind == "affine":
            return 8
        return 8 if (self.bgcnt & (1 << 7)) else 4

    @property
    def palette_base(self) -> int:
        """Return the absolute BG palette base for the engine."""
        return _ENGINE_PALETTE_BASE[self.engine]

    def cell_from_screen(self, screen_x: int, screen_y: int) -> ScreenCell:
        """Resolve a screen pixel to the BG cell, applying the layer scroll.

        ``screen_x``/``screen_y`` are in the engine's 256×192 screen space. The
        scroll is applied modulo the map size; only text backgrounds are supported
        in this version (affine/rotation is a follow-up).

        Parameters:
            screen_x (int): Screen X (0..255).
            screen_y (int): Screen Y (0..191).

        Returns:
            ScreenCell: The map cell info, screen rectangle and scroll used.

        Raises:
            ValueError: If the coordinate is out of the screen or the BG is not text.
        """
        if not 0 <= screen_x < 256 or not 0 <= screen_y < 192:
            raise ValueError("coordenada de tela deve estar em 0..255 / 0..191")
        kind = self.kind
        if kind != "text":
            raise ValueError(
                f"BG {self.bg} é {kind}; cell_from_screen suporta text nesta versão "
                "(affine/rotation é follow-up)"
            )
        width, height = self.map_size
        map_x = (screen_x + self.hofs) % width
        map_y = (screen_y + self.vofs) % height
        info = self.cell(map_x, map_y)
        screen_cell_x = screen_x // 8
        screen_cell_y = screen_y // 8
        return ScreenCell(
            info=info,
            screen_x=screen_x,
            screen_y=screen_y,
            screen_cell_x=screen_cell_x,
            screen_cell_y=screen_cell_y,
            screen_rect=(screen_cell_x * 8, screen_cell_y * 8, 8, 8),
            map_x=map_x,
            map_y=map_y,
            hofs=self.hofs,
            vofs=self.vofs,
        )

    def cell(self, x: int, y: int) -> BgCellInfo:
        """Locate the map entry of the cell at pixel ``(x, y)``."""
        kind = self.kind
        if kind not in ("text", "affine"):
            raise ValueError(
                f"BG {self.bg} é {kind}; map_cell suporta text/affine nesta versão"
            )
        width, height = self.map_size
        if x < 0 or y < 0 or x >= width or y >= height:
            raise ValueError(f"célula ({x},{y}) fora do mapa {width}x{height}")
        cell_x = x // 8
        cell_y = y // 8
        if kind == "text":
            columns = max(1, width // 256)
            block_x = cell_x // 32
            block_y = cell_y // 32
            index = (
                (block_y * columns + block_x) * 1024
                + (cell_y % 32) * 32
                + (cell_x % 32)
            )
            entry_addr = self.screen_base + index * 2
        else:
            index = cell_y * (width // 8) + cell_x
            entry_addr = self.screen_base + index
        return BgCellInfo(
            engine=self.engine,
            bg=self.bg,
            kind=kind,
            x=x,
            y=y,
            cell_x=cell_x,
            cell_y=cell_y,
            entry_addr=entry_addr,
            char_base=self.char_base,
            screen_base=self.screen_base,
            map_width=width,
            map_height=height,
            bpp=self.bpp,
        )

    def decode(self, info: BgCellInfo, entry: int) -> BgCell:
        """Decode a text (16-bit) or affine (8-bit) map entry."""
        if info.kind == "text":
            tile = entry & 0x3FF
            palette: int | None = (entry >> 12) & 0xF
            flip_h = bool(entry & (1 << 10))
            flip_v = bool(entry & (1 << 11))
        else:
            tile = entry & 0xFF
            palette = None
            flip_h = False
            flip_v = False
        return BgCell(
            engine=info.engine,
            bg=info.bg,
            kind=info.kind,
            x=info.x,
            y=info.y,
            cell_x=info.cell_x,
            cell_y=info.cell_y,
            entry_addr=info.entry_addr,
            entry=entry,
            tile_index=tile,
            tile_addr=info.char_base + tile * (64 if info.bpp == 8 else 32),
            palette=palette,
            bpp=info.bpp,
            flip_h=flip_h,
            flip_v=flip_v,
            char_base=info.char_base,
            screen_base=info.screen_base,
            map_width=info.map_width,
            map_height=info.map_height,
        )


@dataclass(frozen=True, slots=True)
class ObjTileMapping:
    """OBJ tile mapping behavior for one engine, from the raw DISPCNT."""

    engine: str
    dispcnt: int

    @classmethod
    def from_registers(cls, engine: str, dispcnt: int) -> "ObjTileMapping":
        """Build the mapping for ``engine``."""
        key = engine.upper()
        if key not in ("A", "B"):
            raise ValueError("engine deve ser 'A' ou 'B'")
        return cls(key, dispcnt)

    def address(self, tile_index: int, bpp: int) -> int:
        """Return the absolute tile address for the current mapping."""
        if bpp not in (4, 8):
            raise ValueError("bpp deve ser 4 ou 8")
        base = _ENGINE_OBJ_BASE[self.engine]
        bytes_per_tile = 64 if bpp == 8 else 32
        if self.dispcnt & (1 << 4):
            boundary = 32 << ((self.dispcnt >> 20) & 0x3)
            return base + tile_index * boundary
        mask_x = 0x0F if bpp == 8 else 0x1F
        shift = 4 if bpp == 8 else 5
        return (
            base
            + (tile_index & mask_x) * bytes_per_tile
            + (tile_index >> shift) * 0x400
        )
