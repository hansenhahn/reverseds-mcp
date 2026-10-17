"""Application service: decode video state and VRAM layout (over the Debugger port)."""
from dataclasses import dataclass

from ..domain.io import DecodedRegister, IoMap, VramBinding, VramLayout
from .ports import Debugger

# VRAMCNT_A..I: A..G at 0x240..0x246, H at 0x248, I at 0x249 (WRAMCNT at 0x247).
_BANK_ADDR = {
    "A": 0x04000240, "B": 0x04000241, "C": 0x04000242, "D": 0x04000243,
    "E": 0x04000244, "F": 0x04000245, "G": 0x04000246,
    "H": 0x04000248, "I": 0x04000249,
}
_ENGINE_BASE = {"A": 0x04000000, "B": 0x04001000}
_POWCNT1 = 0x04000304


@dataclass(frozen=True, slots=True)
class VideoState:
    """Decoded video state of one engine."""

    engine: str
    screen: str
    dispcnt: DecodedRegister
    bgs: tuple[DecodedRegister, ...]
    master_bright: DecodedRegister


class VideoReader:
    """Service: read video registers and the VRAM layout through the Debugger."""

    def __init__(self, debugger: Debugger, io_map: IoMap) -> None:
        """Build the service.

        Parameters:
            debugger (Debugger): A connected debug backend.
            io_map (IoMap): The IO register map.
        """
        self._debugger = debugger
        self._io_map = io_map

    def _decode(self, addr: int, size: int) -> DecodedRegister:
        decoded = self._io_map.decode(addr, self._debugger.read_memory(addr, size))
        assert decoded is not None
        return decoded

    def state(self, engine: str) -> VideoState:
        """Read the decoded state of ``engine`` (``A`` or ``B``).

        Parameters:
            engine (str): ``A`` or ``B``.

        Returns:
            VideoState: The decoded state, with the engine's screen (top/bottom).
        """
        key = engine.upper()
        base = _ENGINE_BASE[key]
        dispcnt = self._decode(base, 4)
        bgs = tuple(self._decode(base + 8 + 2 * i, 2) for i in range(4))
        master_bright = self._decode(base + 0x6C, 2)
        swap = {f.name: f.value for f in self._decode(_POWCNT1, 2).fields}["display_swap"]
        top_engine = "A" if swap else "B"
        screen = "top" if key == top_engine else "bottom"
        return VideoState(key, screen, dispcnt, bgs, master_bright)

    def vram_layout(self) -> list[VramBinding]:
        """Read the current ``VRAMCNT`` bytes and resolve the bank→window layout.

        Returns:
            list[VramBinding]: The active VRAM bindings.
        """
        banks = {
            bank: self._debugger.read_memory(addr, 1)[0]
            for bank, addr in _BANK_ADDR.items()
        }
        return VramLayout.from_vramcnt(banks).bindings()

    def read_vram(self, addr: int, size: int) -> bytes:
        """Read ``size`` bytes of VRAM at ``addr``.

        Parameters:
            addr (int): The VRAM address (e.g. ``0x06000000``).
            size (int): Number of bytes.

        Returns:
            bytes: The bytes read.
        """
        return self._debugger.read_memory(addr, size)
