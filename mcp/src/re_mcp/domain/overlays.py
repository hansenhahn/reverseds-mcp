"""Overlay tables (y9/y7) of the cartridge: entities and aggregate, without I/O.

Overlays are described by the ROM header (`arm9_overlay`/`arm7_overlay`); each one's
data lives in the FAT as ordinary files.
"""
import struct
from dataclasses import dataclass, replace

_ENTRY_SIZE = 32
_COMPRESSED_SIZE_MASK = 0x00FFFFFF


@dataclass(frozen=True, slots=True)
class Overlay:
    """An overlay entry: where it loads in RAM and which file carries its data."""

    core: str
    index: int
    ram_address: int
    ram_size: int
    bss_size: int
    file_id: int
    sinit_start: int = 0
    sinit_end: int = 0
    flags: int = 0
    compressed_size: int = 0

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
    """Resolution of a RAM address: the overlay and the offsets inside it.

    ``offset_file`` is relative to ``ram_address``; ``offset_code`` is relative to
    ``code_base`` (when the caller knows the overlay's code base/prefix).
    """

    overlay: Overlay
    offset_file: int
    offset_code: int | None = None

    @property
    def offset(self) -> int:
        """Backward-compatible alias for ``offset_file``."""
        return self.offset_file


@dataclass(frozen=True, slots=True)
class OverlayDetails:
    """An overlay enriched with FAT and compression data."""

    overlay: Overlay
    file_offset: int
    file_size: int
    compressed: bool
    compressed_size: int
    code_base: int | None = None
    prefix_size: int | None = None

    @property
    def index(self) -> int:
        """The overlay ID."""
        return self.overlay.index

    @property
    def core(self) -> str:
        """The core (``arm9``/``arm7``)."""
        return self.overlay.core

    def with_code_base(self, code_base: int | None) -> "OverlayDetails":
        """Return a copy with ``code_base``/``prefix_size`` set and validated.

        Parameters:
            code_base (int | None): Address where the overlay's code starts. When
                ``None`` the details are returned unchanged.

        Returns:
            OverlayDetails: The details with the optional code base.

        Raises:
            ValueError: If ``code_base`` is outside the overlay's RAM range.
        """
        if code_base is None:
            return self
        start = self.overlay.ram_address
        if not start <= code_base < start + self.overlay.ram_size:
            raise ValueError("code_base fora do intervalo da overlay")
        return replace(self, code_base=code_base, prefix_size=code_base - start)


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
            idx, ram, size, bss, sinit_start, sinit_end, file_id, flags = (
                struct.unpack_from("<8I", data, off)
            )
            overlays.append(
                Overlay(
                    core=core,
                    index=idx,
                    ram_address=ram,
                    ram_size=size,
                    bss_size=bss,
                    file_id=file_id,
                    sinit_start=sinit_start,
                    sinit_end=sinit_end,
                    flags=flags,
                    compressed_size=flags & _COMPRESSED_SIZE_MASK,
                )
            )
        return cls(overlays)

    def entries(self) -> list[Overlay]:
        """The overlay entries."""
        return list(self._overlays)

    def by_index(self, index: int) -> Overlay | None:
        """The overlay with ``index`` (overlay ID), or None.

        Parameters:
            index (int): The overlay ID.

        Returns:
            Overlay | None: The entry, or None.
        """
        for overlay in self._overlays:
            if overlay.index == index:
                return overlay
        return None

    def candidates(self, addr: int) -> tuple[OverlayHit, ...]:
        """All overlays covering ``addr`` (shared bases yield multiple hits).

        Parameters:
            addr (int): A RAM address.

        Returns:
            tuple[OverlayHit, ...]: The candidates, in table order.
        """
        return tuple(
            OverlayHit(overlay, addr - overlay.ram_address)
            for overlay in self._overlays
            if overlay.covers(addr)
        )

    def for_address(self, addr: int) -> OverlayHit | None:
        """Resolve a RAM address to the first overlay that contains it.

        Prefer :meth:`candidates` when overlays may share a base.

        Parameters:
            addr (int): A RAM address.

        Returns:
            OverlayHit | None: The first overlay and its offset, or None.
        """
        hits = self.candidates(addr)
        return hits[0] if hits else None
