"""Pure stack scanning for a backtrace fallback (no I/O)."""
from collections.abc import Iterable

from .addresses import MemoryRegion

CODE_REGIONS: tuple[MemoryRegion, ...] = (
    MemoryRegion("itcm", 0x00000000, 0x00007FFF),
    MemoryRegion("main-ram", 0x02000000, 0x023FFFFF),
    MemoryRegion("arm9-bios", 0xFFFF0000, 0xFFFFFFFF),
)


class StackScanner:
    """Scan a stack snapshot for candidate return addresses."""

    def __init__(
        self,
        exclude: Iterable[int] = (),
        exclude_range: tuple[int, int] | None = None,
        limit: int = 32,
        regions: tuple[MemoryRegion, ...] = CODE_REGIONS,
    ) -> None:
        """Configure the scan.

        Parameters:
            exclude: Addresses to skip (current PC, known frames).
            exclude_range: Half-open range to skip (the stack).
            limit: Maximum number of candidates to return.
            regions: Code regions a candidate must fall inside.
        """
        self._exclude = frozenset(exclude)
        self._exclude_range = exclude_range
        self._limit = limit
        self._regions = regions

    def scan(self, stack: bytes) -> tuple[int, ...]:
        """Find candidate return addresses in a stack snapshot.

        Each 4-byte word is considered a candidate when it is even (ARM/Thumb
        alignment), falls inside a known code region, is not excluded and is not
        inside the stack range itself.

        Parameters:
            stack (bytes): The stack bytes (usually ``sp..sp+depth``).

        Returns:
            tuple[int, ...]: Candidates in stack order, deduplicated.
        """
        if self._limit <= 0:
            return ()
        seen = set(self._exclude)
        found: list[int] = []
        low, high = (
            self._exclude_range if self._exclude_range is not None else (0, 0)
        )
        for offset in range(0, len(stack) - 3, 4):
            addr = int.from_bytes(stack[offset:offset + 4], "little")
            if addr % 2 != 0 or addr in seen:
                continue
            if self._exclude_range is not None and low <= addr < high:
                continue
            if not any(region.covers(addr) for region in self._regions):
                continue
            seen.add(addr)
            found.append(addr)
            if len(found) >= self._limit:
                break
        return tuple(found)
