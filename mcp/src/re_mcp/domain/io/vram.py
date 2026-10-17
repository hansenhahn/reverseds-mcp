"""VRAM bank→window layout, following GBATEK's "VRAM Bank Control" table (pure)."""
from dataclasses import dataclass

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
        return _lcdc(bank)
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
