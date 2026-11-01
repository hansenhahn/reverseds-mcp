"""BG/OBJ display helpers (pure): map cells, tile addresses and VRAM layout."""
from dataclasses import dataclass

_TEXT_SIZES = ((256, 256), (512, 256), (256, 512), (512, 512))
_AFFINE_SIZES = ((128, 128), (256, 256), (512, 512), (1024, 1024))
_ENGINE_BG_BASE = {"A": 0x06000000, "B": 0x06200000}
_ENGINE_OBJ_BASE = {"A": 0x06400000, "B": 0x06600000}


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


def bg_kind(dispcnt: int, engine: str, bg: int) -> str:
    """Return the BG layer kind (text/affine/extended/3d/large/invalid)."""
    mode = dispcnt & 0x7
    if mode == 6:
        if engine == "A" and bg == 0:
            return "3d"
        return "large" if bg == 2 else "invalid"
    if engine == "A" and bg == 0 and (dispcnt & (1 << 3)):
        return "3d"
    if mode == 0:
        return "text"
    if mode == 1:
        return "affine" if bg == 2 else "text"
    if mode == 2:
        return "affine" if bg in (2, 3) else "text"
    if mode == 3:
        return "extended" if bg == 3 else "text"
    if mode == 4:
        return "affine" if bg == 2 else ("extended" if bg == 3 else "text")
    if mode == 5:
        return "extended" if bg in (2, 3) else "text"
    return "invalid"


def bg_map_size(bgcnt: int, kind: str) -> tuple[int, int]:
    """Return the BG map size in pixels."""
    size = (bgcnt >> 14) & 0x3
    table = _AFFINE_SIZES if kind == "affine" else _TEXT_SIZES
    return table[size]


def bg_char_base(dispcnt: int, bgcnt: int, engine: str) -> int:
    """Return the absolute BG character base address."""
    base = _ENGINE_BG_BASE[engine]
    value = ((bgcnt >> 2) & 0x3) * 0x4000
    if engine == "A":
        value += ((dispcnt >> 24) & 0x7) * 0x10000
    return base + value


def bg_screen_base(dispcnt: int, bgcnt: int, engine: str) -> int:
    """Return the absolute BG screen (map) base address."""
    base = _ENGINE_BG_BASE[engine]
    value = ((bgcnt >> 8) & 0x1F) * 0x800
    if engine == "A":
        value += ((dispcnt >> 27) & 0x7) * 0x10000
    return base + value


def cell_info(
    dispcnt: int, bgcnt: int, engine: str, bg: int, x: int, y: int
) -> BgCellInfo:
    """Locate the map entry for a BG cell."""
    kind = bg_kind(dispcnt, engine, bg)
    if kind not in ("text", "affine"):
        raise ValueError(f"BG {bg} é {kind}; map_cell suporta text/affine nesta versão")
    width, height = bg_map_size(bgcnt, kind)
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
        entry_addr = bg_screen_base(dispcnt, bgcnt, engine) + index * 2
        bpp = 8 if (bgcnt & (1 << 7)) else 4
    else:
        index = cell_y * (width // 8) + cell_x
        entry_addr = bg_screen_base(dispcnt, bgcnt, engine) + index
        bpp = 8
    return BgCellInfo(
        engine=engine,
        bg=bg,
        kind=kind,
        x=x,
        y=y,
        cell_x=cell_x,
        cell_y=cell_y,
        entry_addr=entry_addr,
        char_base=bg_char_base(dispcnt, bgcnt, engine),
        screen_base=bg_screen_base(dispcnt, bgcnt, engine),
        map_width=width,
        map_height=height,
        bpp=bpp,
    )


def decode_cell(info: BgCellInfo, entry: int) -> BgCell:
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
    tile_addr = info.char_base + tile * (64 if info.bpp == 8 else 32)
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
        tile_addr=tile_addr,
        palette=palette,
        bpp=info.bpp,
        flip_h=flip_h,
        flip_v=flip_v,
        char_base=info.char_base,
        screen_base=info.screen_base,
        map_width=info.map_width,
        map_height=info.map_height,
    )


def obj_tile_address(dispcnt: int, engine: str, tile_index: int, bpp: int) -> int:
    """Return the absolute OBJ tile address for the current mapping."""
    base = _ENGINE_OBJ_BASE[engine]
    bytes_per_tile = 64 if bpp == 8 else 32
    if dispcnt & (1 << 4):
        boundary = 32 << ((dispcnt >> 20) & 0x3)
        return base + tile_index * boundary
    mask_x = 0x0F if bpp == 8 else 0x1F
    shift = 4 if bpp == 8 else 5
    return base + (tile_index & mask_x) * bytes_per_tile + (tile_index >> shift) * 0x400
