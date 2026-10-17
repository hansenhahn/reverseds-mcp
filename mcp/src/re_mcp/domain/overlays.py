"""Overlay tables (y9/y7) of the cartridge: entities and aggregate, without I/O.

Overlays are described by the ROM header (`arm9_overlay`/`arm7_overlay`); each one's
data lives in the FAT as ordinary files.
"""
import struct
from dataclasses import dataclass

_ENTRY_SIZE = 32


@dataclass(frozen=True, slots=True)
class Overlay:
    """An overlay entry: where it loads in RAM and which file carries its data."""

    core: str
    index: int
    ram_address: int
    ram_size: int
    bss_size: int
    file_id: int

    def covers(self, addr: int) -> bool:
        """Whether ``addr`` falls in the RAM occupied by this overlay.

        Parameters:
            addr (int): A RAM address.

        Returns:
            bool: True if ``ram_address <= addr < ram_address + ram_size``.
        """
        return self.ram_address <= addr < self.ram_address + self.ram_size


@dataclass(frozen=True, slots=True)
class OverlayHit:
    """Resolution of a RAM address: the overlay and the offset inside it."""

    overlay: Overlay
    offset: int


class OverlayTable:
    """Aggregate: the overlay entries of one core (ARM9/ARM7)."""

    def __init__(self, overlays: list[Overlay]) -> None:
        self._overlays = overlays

    @classmethod
    def from_bytes(cls, data: bytes, core: str) -> "OverlayTable":
        """Parse an overlay table (32 bytes per entry).

        Parameters:
            data (bytes): The table contents (`arm9_overlay` or `arm7_overlay`).
            core (str): ``arm9`` or ``arm7``, to label the entries.

        Returns:
            OverlayTable: The overlay entries.
        """
        overlays: list[Overlay] = []
        for off in range(0, len(data) - (_ENTRY_SIZE - 1), _ENTRY_SIZE):
            idx, ram, size, bss, _si, _sie, file_id, _res = struct.unpack_from(
                "<8I", data, off
            )
            overlays.append(
                Overlay(
                    core=core,
                    index=idx,
                    ram_address=ram,
                    ram_size=size,
                    bss_size=bss,
                    file_id=file_id,
                )
            )
        return cls(overlays)

    def entries(self) -> list[Overlay]:
        """The overlay entries."""
        return list(self._overlays)

    def for_address(self, addr: int) -> OverlayHit | None:
        """Resolve a RAM address to the overlay that contains it.

        Parameters:
            addr (int): A RAM address.

        Returns:
            OverlayHit | None: The overlay and the offset, or None.
        """
        for overlay in self._overlays:
            if overlay.covers(addr):
                return OverlayHit(overlay, addr - overlay.ram_address)
        return None
