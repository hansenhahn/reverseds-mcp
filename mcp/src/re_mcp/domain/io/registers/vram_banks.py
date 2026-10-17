"""VRAM/WRAM bank control — GBATEK "VRAMCNT_A..I" and "WRAMCNT"."""
from ..decode import Register
from ._fields import bit, bits

# VRAMCNT A..G at 0x240..0x246, WRAMCNT at 0x247, VRAMCNT H/I at 0x248/0x249.
_VRAMCNT_ADDR = {
    "A": 0x04000240, "B": 0x04000241, "C": 0x04000242, "D": 0x04000243,
    "E": 0x04000244, "F": 0x04000245, "G": 0x04000246,
    "H": 0x04000248, "I": 0x04000249,
}
_WRAMCNT_ADDR = 0x04000247


def vram_registers() -> list[Register]:
    """The VRAM and WRAM bank control registers.

    Returns:
        list[Register]: VRAMCNT_A..I and WRAMCNT.

    Note:
        GBATEK marks the VRAMCNT registers as write-only; melonDS exposes the stored
        value on reads, so they can be decoded live.
    """
    vramcnt = (
        bits("mst", 0, 2, (), "Mapping mode (bank-dependent; see the GBATEK table)"),
        bits("offset", 3, 4, (), "Offset (bank-dependent)"),
        bit("enable", 7, (), "Bank enable"),
    )
    wramcnt = (
        bits("wram", 0, 1, ((0, "4K arm7"), (1, "2K ea"), (2, "arm9 only")),
             "WRAM mapping"),
    )
    registers = [
        Register(f"VRAMCNT_{bank}", addr, 1, vramcnt, f"VRAM bank {bank} control")
        for bank, addr in _VRAMCNT_ADDR.items()
    ]
    registers.append(Register("WRAMCNT", _WRAMCNT_ADDR, 1, wramcnt, "WRAM bank control"))
    return registers
