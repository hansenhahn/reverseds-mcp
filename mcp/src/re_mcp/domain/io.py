"""IO map of the NDS: register schema and pure decoders (no I/O).

The schema is derived from GBATEK (the reference the melonDS itself credits) and
covers the initial scope: 2D video/BG, 3D control, power, VRAM/WRAM banks and DMA.
`decode_io` turns raw bytes into named fields; `vram_layout` turns the VRAMCNT values
into bank→window bindings, following GBATEK's "VRAM Bank Control" table.
"""
from dataclasses import dataclass

# --- decoded value types ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegField:
    """A bitfield of a register: name, bit range and optional value names."""

    name: str
    low: int
    high: int
    values: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Register:
    """A memory-mapped register: name, address, size and bitfields."""

    name: str
    address: int
    size: int
    fields: tuple[RegField, ...]


@dataclass(frozen=True, slots=True)
class DecodedField:
    """A decoded bitfield: name, value and its meaning when the schema names it."""

    name: str
    value: int
    meaning: str | None


@dataclass(frozen=True, slots=True)
class DecodedRegister:
    """A decoded register: raw value plus the named fields."""

    name: str
    address: int
    size: int
    raw: int
    fields: tuple[DecodedField, ...]


def _bit(name: str, low: int, values: tuple[tuple[int, str], ...] = ()) -> RegField:
    return RegField(name, low, low, values)


def _bits(
    name: str, low: int, high: int, values: tuple[tuple[int, str], ...] = ()
) -> RegField:
    return RegField(name, low, high, values)


# --- schema ----------------------------------------------------------------------

_DISPCNT_FIELDS = (
    _bits("bg_mode", 0, 2, tuple((m, f"mode {m}") for m in range(6))),
    _bit("frame", 4, ((0, "frame 0"), (1, "frame 1"))),
    _bit("hblank_oam", 5),
    _bit("obj_1d_mapping", 6),
    _bit("forced_blank", 7),
    _bit("bg0_enable", 8),
    _bit("bg1_enable", 9),
    _bit("bg2_enable", 10),
    _bit("bg3_enable", 11),
    _bit("obj_enable", 12),
    _bit("win0_enable", 13),
    _bit("win1_enable", 14),
    _bit("obj_win_enable", 15),
    _bits(
        "display_mode",
        16,
        17,
        ((0, "display off"), (1, "graphics"), (2, "reserved"), (3, "main memory")),
    ),
)

_DISP3DCNT_FIELDS = (
    _bit("texture_mapping", 0),
    _bit("shading", 1, ((0, "toon"), (1, "highlight"))),
    _bit("alpha_test", 2),
    _bit("alpha_blending", 3),
    _bit("anti_aliasing", 4),
    _bit("edge_marking", 5),
    _bit("fog_alpha_only", 6),
    _bit("fog_enable", 7),
    _bits("fog_shift", 8, 11),
    _bit("rdlines_underflow", 12),
    _bit("poly_overflow", 13),
    _bit("rear_plane", 14, ((0, "blank"), (1, "bitmap"))),
)

_POWCNT1_FIELDS = (
    _bit("lcd_enable", 0),
    _bit("engine_a_2d", 1),
    _bit("engine_3d_render", 2),
    _bit("engine_3d_geometry", 3),
    _bit("engine_b_2d", 9),
    _bit("display_swap", 15, ((0, "A to lower"), (1, "A to upper"))),
)

_BGxCNT_FIELDS = (
    _bits("priority", 0, 1, ((0, "highest"), (3, "lowest"))),
    _bits("char_base", 2, 3),
    _bit("mosaic", 6),
    _bit("colors", 7, ((0, "16/16"), (1, "256/1"))),
    _bits("screen_base", 8, 12),
    _bit("area_overflow", 13, ((0, "transparent"), (1, "wrap"))),
    _bits("screen_size", 14, 15),
)

_MASTER_BRIGHT_FIELDS = (
    _bits("factor", 0, 4),
    _bits("mode", 14, 15, ((0, "disable"), (1, "up"), (2, "down"), (3, "reserved"))),
)

_DMACNT_FIELDS = (
    _bits("word_count", 0, 20),
    _bits(
        "dest_control",
        21,
        22,
        ((0, "inc"), (1, "dec"), (2, "fixed"), (3, "inc/reload")),
    ),
    _bits("src_control", 23, 24, ((0, "inc"), (1, "dec"), (2, "fixed"))),
    _bit("repeat", 25),
    _bit("transfer_32bit", 26),
    _bits(
        "start_timing",
        27,
        29,
        (
            (0, "immediately"),
            (1, "v-blank"),
            (2, "h-blank"),
            (3, "display sync"),
            (4, "main memory display"),
            (5, "cart slot"),
            (6, "gba slot"),
            (7, "geometry fifo"),
        ),
    ),
    _bit("irq", 30),
    _bit("enable", 31),
)

_VRAMCNT_FIELDS = (_bits("mst", 0, 2), _bits("offset", 3, 4), _bit("enable", 7))
_WRAMCNT_FIELDS = (_bits("wram", 0, 1, ((0, "4K arm7"), (1, "2K ea"), (2, "arm9 only"))),)

_SCHEMA: dict[int, Register] = {}


def _add(reg: Register) -> None:
    _SCHEMA[reg.address] = reg


_add(Register("DISPCNT_A", 0x04000000, 4, _DISPCNT_FIELDS))
_add(Register("DISPCNT_B", 0x04001000, 4, _DISPCNT_FIELDS))
for _i in range(4):
    _add(Register(f"BG{_i}CNT_A", 0x04000008 + 2 * _i, 2, _BGxCNT_FIELDS))
    _add(Register(f"BG{_i}CNT_B", 0x04001008 + 2 * _i, 2, _BGxCNT_FIELDS))
_add(Register("DISP3DCNT", 0x04000060, 4, _DISP3DCNT_FIELDS))
_add(Register("MASTER_BRIGHT_A", 0x0400006C, 2, _MASTER_BRIGHT_FIELDS))
_add(Register("MASTER_BRIGHT_B", 0x0400106C, 2, _MASTER_BRIGHT_FIELDS))
_add(Register("POWCNT1", 0x04000304, 2, _POWCNT1_FIELDS))
for _i in range(4):
    _add(Register(f"DMA{_i}CNT", 0x040000B8 + 12 * _i, 4, _DMACNT_FIELDS))
# VRAMCNT A..G at 0x240..0x246, WRAMCNT at 0x247, VRAMCNT H/I at 0x248/0x249.
_VRAMCNT_ADDR = {
    "A": 0x04000240, "B": 0x04000241, "C": 0x04000242, "D": 0x04000243,
    "E": 0x04000244, "F": 0x04000245, "G": 0x04000246,
    "H": 0x04000248, "I": 0x04000249,
}
for _bank, _addr in _VRAMCNT_ADDR.items():
    _add(Register(f"VRAMCNT_{_bank}", _addr, 1, _VRAMCNT_FIELDS))
_add(Register("WRAMCNT", 0x04000247, 1, _WRAMCNT_FIELDS))


def decode_io(addr: int, data: bytes) -> DecodedRegister | None:
    """Decode the IO register at ``addr`` from its bytes.

    Parameters:
        addr (int): The IO address (e.g. ``0x04000000`` for DISPCNT A).
        data (bytes): The bytes read at that address.

    Returns:
        DecodedRegister | None: The decoded register, or None if the address is not
        covered by the schema.
    """
    register = register_at(addr)
    if register is None:
        return None
    raw = int.from_bytes(data[: register.size], "little")
    decoded = []
    for spec in register.fields:
        width = spec.high - spec.low + 1
        value = (raw >> spec.low) & ((1 << width) - 1)
        meaning = dict(spec.values).get(value) if spec.values else None
        decoded.append(DecodedField(spec.name, value, meaning))
    return DecodedRegister(
        register.name, addr, register.size, raw, tuple(decoded)
    )


class UnknownRegister(ValueError):
    """The address is not covered by the IO schema."""


def register_at(addr: int) -> Register | None:
    """The register definition at ``addr``, or None if not in the schema.

    Parameters:
        addr (int): The IO address.

    Returns:
        Register | None: The register definition, or None.
    """
    return _SCHEMA.get(addr)


# --- VRAM layout (GBATEK "VRAM Bank Control" table) ------------------------------

VRAM_BANK_SIZE = {
    "A": 0x20000, "B": 0x20000, "C": 0x20000, "D": 0x20000,
    "E": 0x10000, "F": 0x4000, "G": 0x4000, "H": 0x8000, "I": 0x4000,
}


@dataclass(frozen=True, slots=True)
class VramBinding:
    """How a VRAM bank is mapped, per the GBATEK table."""

    bank: str
    mst: int
    offset: int
    target: str
    address: int | None


def _lcdc(bank: str) -> tuple[str, int]:
    base = 0x6800000
    index = "ABCD".find(bank)
    if index >= 0:
        return "lcdc", base + index * 0x20000
    if bank == "E":
        return "lcdc", 0x6880000
    return "lcdc", {"F": 0x6890000, "G": 0x6894000, "H": 0x6898000, "I": 0x68A0000}[bank]


def _engine_a_bg(bank: str, ofs: int) -> tuple[str, int] | None:
    if bank in "ABCD":
        return "engine_a_bg", 0x6000000 + 0x20000 * ofs
    if bank == "E":
        return "engine_a_bg", 0x6000000
    if bank in "FG":
        return "engine_a_bg", 0x6000000 + 0x4000 * (ofs & 1) + 0x10000 * ((ofs >> 1) & 1)
    return None


def _engine_a_obj(bank: str, ofs: int) -> tuple[str, int] | None:
    if bank in "AB":
        return "engine_a_obj", 0x6400000 + 0x20000 * (ofs & 1)
    if bank == "E":
        return "engine_a_obj", 0x6400000
    if bank in "FG":
        return "engine_a_obj", 0x6400000 + 0x4000 * (ofs & 1) + 0x10000 * ((ofs >> 1) & 1)
    return None


def _bind(bank: str, mst: int, ofs: int) -> tuple[str, int | None] | None:
    if mst == 0:
        target, addr = _lcdc(bank)
        return target, addr
    if mst == 1:
        if bank in "ABCDEFG":
            return _engine_a_bg(bank, ofs)
        if bank == "H":
            return "engine_b_bg", 0x6200000
        if bank == "I":
            return "engine_b_bg", 0x6208000
    if mst == 2:
        if bank in "ABEFG":
            return _engine_a_obj(bank, ofs)
        if bank in "CD":
            return "arm7_plain", 0x6000000 + 0x20000 * (ofs & 1)
        if bank == "H":
            return "engine_b_bg_extpal", None
        if bank == "I":
            return "engine_b_obj", 0x6600000
    if mst == 3:
        if bank in "ABCD":
            return f"texture_image_slot{ofs}", None
        if bank in "EFG":
            return "texture_palette", None
        if bank == "I":
            return "engine_b_obj_extpal", None
    if mst == 4:
        if bank == "C":
            return "engine_b_bg", 0x6200000
        if bank == "D":
            return "engine_b_obj", 0x6600000
        if bank in "EFG":
            return "engine_a_bg_extpal", None
    if mst == 5 and bank in "FG":
        return "engine_a_obj_extpal", None
    return None


def vram_layout(banks: dict[str, int]) -> list[VramBinding]:
    """Resolve the VRAMCNT bytes into bank→window bindings (GBATEK table).

    Parameters:
        banks (dict[str, int]): The ``VRAMCNT_A..I`` byte values, keyed by bank letter.

    Returns:
        list[VramBinding]: The bindings for the enabled banks (disabled ones omitted).
    """
    bindings: list[VramBinding] = []
    for bank in "ABCDEFGHI":
        value = banks.get(bank, 0)
        if not (value & 0x80):
            continue
        mst = value & 0x07
        ofs = (value >> 3) & 0x03
        resolved = _bind(bank, mst, ofs)
        if resolved is None:
            continue
        target, address = resolved
        bindings.append(VramBinding(bank, mst, ofs, target, address))
    return bindings
