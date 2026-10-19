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


@dataclass(frozen=True, slots=True)
class Breakpoint:
    """A breakpoint or watchpoint known to the stub."""

    number: int
    kind: str
    address: int | None
    condition: str | None
    enabled: bool


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
