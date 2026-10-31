"""Pure stack scanning for a backtrace fallback (no I/O)."""
from collections.abc import Iterable

from .addresses import MemoryRegion

CODE_REGIONS: tuple[MemoryRegion, ...] = (
    MemoryRegion("itcm", 0x00000000, 0x00007FFF),
    MemoryRegion("main-ram", 0x02000000, 0x023FFFFF),
    MemoryRegion("arm9-bios", 0xFFFF0000, 0xFFFFFFFF),
)


def scan_return_addresses(
    stack: bytes,
    exclude: Iterable[int] = (),
    exclude_range: tuple[int, int] | None = None,
    limit: int = 32,
) -> tuple[int, ...]:
    """Find candidate return addresses in a stack snapshot.

    Each 4-byte word is considered a candidate when it is even (ARM/Thumb
    alignment), falls inside a known code region, is not excluded and is not
    inside the stack range itself.

    Parameters:
        stack (bytes): The stack bytes (usually ``sp..sp+depth``).
        exclude (Iterable[int]): Addresses to skip (current PC, known frames).
        exclude_range (tuple[int, int] | None): Half-open range to skip (the stack).
        limit (int): Maximum number of candidates to return.

    Returns:
        tuple[int, ...]: Candidates in stack order, deduplicated.
    """
    if limit <= 0:
        return ()
    seen = set(exclude)
    found: list[int] = []
    low, high = exclude_range if exclude_range is not None else (0, 0)
    for offset in range(0, len(stack) - 3, 4):
        addr = int.from_bytes(stack[offset:offset + 4], "little")
        if addr % 2 != 0 or addr in seen:
            continue
        if exclude_range is not None and low <= addr < high:
            continue
        if not any(region.covers(addr) for region in CODE_REGIONS):
            continue
        seen.add(addr)
        found.append(addr)
        if len(found) >= limit:
            break
    return tuple(found)
