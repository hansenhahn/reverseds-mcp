"""Debug model: watchpoint hits, snapshots and memory diff (pure)."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WatchpointHit:
    """A watchpoint stop: PC and register context."""

    pc: int
    registers: dict[str, int]


@dataclass(frozen=True, slots=True)
class StackFrame:
    """One frame of a backtrace."""

    index: int
    pc: int
    function: str | None
    source: str = "gdb"


@dataclass(frozen=True, slots=True)
class Breakpoint:
    """A breakpoint or watchpoint known to the stub."""

    number: int
    kind: str
    address: int | None
    condition: str | None
    enabled: bool
    hardware: bool = True


@dataclass(frozen=True, slots=True)
class HardwareSlots:
    """Hardware watchpoint usage of the connected core."""

    core: str | None
    limit: int
    breakpoints: tuple[Breakpoint, ...]

    @property
    def watchpoints(self) -> tuple[Breakpoint, ...]:
        """Every watchpoint known to the stub (hardware and software)."""
        return tuple(bp for bp in self.breakpoints if "watchpoint" in bp.kind)

    @property
    def hardware_watchpoints(self) -> tuple[Breakpoint, ...]:
        """The watchpoints actually using a hardware slot."""
        return tuple(bp for bp in self.watchpoints if bp.hardware)

    @property
    def software(self) -> tuple[Breakpoint, ...]:
        """Watchpoints running in gdb's software fallback."""
        return tuple(bp for bp in self.watchpoints if not bp.hardware)

    @property
    def used(self) -> int:
        """Number of hardware watchpoint slots in use."""
        return len(self.hardware_watchpoints)

    @property
    def free(self) -> int:
        """Number of free hardware watchpoint slots."""
        return max(0, self.limit - self.used)

    @property
    def by_kind(self) -> dict[str, int]:
        """Hardware watchpoint count per normalized kind."""
        counts: dict[str, int] = {}
        for watchpoint in self.hardware_watchpoints:
            counts[watchpoint.kind] = counts.get(watchpoint.kind, 0) + 1
        return counts


@dataclass(frozen=True, slots=True)
class ArgCheck:
    """One argument-contract check."""

    arg: str
    expected: int | str
    actual: int
    ok: bool


@dataclass(frozen=True, slots=True)
class ArgHit:
    """Arguments captured at a callsite hit."""

    pc: int
    registers: dict[str, int]
    stack: tuple[int, ...]
    checks: tuple[ArgCheck, ...]
    ok: bool


@dataclass(frozen=True, slots=True)
class Snapshot:
    """A stored block of memory, with its base address."""

    addr: int
    data: bytes


@dataclass(frozen=True, slots=True)
class MemoryChange:
    """A byte that changed between two states."""

    addr: int
    old: int
    new: int


@dataclass(frozen=True, slots=True)
class MemoryDiff:
    """Comparison of two memory blocks of the same size."""

    changes: tuple[MemoryChange, ...]

    @classmethod
    def between(cls, before: bytes, after: bytes, base: int) -> "MemoryDiff":
        """Compare two blocks and list the bytes that changed.

        Parameters:
            before (bytes): The previous block.
            after (bytes): The current block.
            base (int): The base address of the block.

        Returns:
            MemoryDiff: The changes ``(addr, old, new)``.
        """
        return cls(
            tuple(
                MemoryChange(base + offset, old, new)
                for offset, (old, new) in enumerate(zip(before, after))
                if old != new
            )
        )

    def __len__(self) -> int:
        return len(self.changes)
