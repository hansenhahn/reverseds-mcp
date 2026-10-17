"""VRAM/WRAM bank control register definitions."""
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
    """
    vramcnt = (bits("mst", 0, 2), bits("offset", 3, 4), bit("enable", 7))
    wramcnt = (bits("wram", 0, 1, ((0, "4K arm7"), (1, "2K ea"), (2, "arm9 only"))),)
    registers = [
        Register(f"VRAMCNT_{bank}", addr, 1, vramcnt)
        for bank, addr in _VRAMCNT_ADDR.items()
    ]
    registers.append(Register("WRAMCNT", _WRAMCNT_ADDR, 1, wramcnt))
    return registers
