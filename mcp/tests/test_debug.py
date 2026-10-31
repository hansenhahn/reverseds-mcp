"""Debug service tests (domain, with a fake Debugger)."""
from re_mcp.application.watchpoints import Watchpoints
from re_mcp.domain.debug import Breakpoint, MemoryDiff, StackFrame


class FakeDebugger:
    """Fake Debugger that satisfies the `Debugger` port."""

    def __init__(self, breakpoints: list[Breakpoint] | None = None) -> None:
        self.removed: int | None = None
        self._breakpoints = breakpoints or []

    def connect(self, core: str) -> None: ...
    def core(self) -> str | None:
        return "arm9"
    def watchpoint_limit(self) -> int:
        return 4
    def write_register(self, name: str, value: int) -> None: ...
    def read_memory(self, addr: int, size: int) -> bytes:
        return b""
    def write_memory(self, addr: int, data: bytes) -> None: ...
    def set_breakpoint(
        self, addr: int, condition: str | None = None, commands: list[str] | None = None
    ) -> int:
        return 0
    def backtrace(self) -> list[StackFrame]:
        return []
    def breakpoints(self) -> list[Breakpoint]:
        return self._breakpoints
    def step(self) -> None: ...
    def interrupt(self) -> None: ...
    def resume(self) -> None: ...
    def wait_stop(self, timeout: float) -> bool:
        return True
    def is_running(self) -> bool:
        return False
    def disconnect(self) -> None: ...
    def close(self) -> None: ...

    def refresh_registers(self) -> None: ...
    def read_register(self, name: str) -> int:
        return 0x02000000 if name == "pc" else 0

    def set_watchpoint(self, addr: int, kind: str, condition: str | None = None) -> int:
        self.watchpoint = (addr, kind, condition)
        return 7

    def continue_(self, timeout: float = 30.0) -> bool:
        return True

    def remove(self, number: int) -> None:
        self.removed = number


def test_memory_diff_lists_changed_bytes() -> None:
    """`MemoryDiff` lists the bytes that changed, with absolute address."""
    diff = MemoryDiff.between(b"\x01\x02\x03", b"\x01\x09\x03", 0x10)
    assert len(diff) == 1
    assert (diff.changes[0].addr, diff.changes[0].old, diff.changes[0].new) == (0x11, 2, 9)


def test_find_write_captures_pc_and_removes_watchpoint() -> None:
    """`find_write` captures the PC on the hit and always removes the watchpoint."""
    debugger = FakeDebugger()
    hit = Watchpoints(debugger).find_write(0x0600F448)
    assert hit is not None
    assert hit.pc == 0x02000000
    assert hit.registers["r0"] == 0
    assert debugger.removed == 7


def test_slots_counts_watchpoints_and_free_slots() -> None:
    """`HardwareSlots` counts only watchpoints and computes free slots."""
    debugger = FakeDebugger(
        breakpoints=[
            Breakpoint(1, "watchpoint", 0x06000000, None, True),
            Breakpoint(2, "read-watchpoint", 0x06000004, "r0 == 1", True),
            Breakpoint(3, "breakpoint", 0x02000000, None, True),
        ]
    )
    slots = Watchpoints(debugger).slots()
    assert (slots.core, slots.limit, slots.used, slots.free) == ("arm9", 4, 2, 2)
    assert slots.by_kind == {"watchpoint": 1, "read-watchpoint": 1}
    assert [bp.number for bp in slots.watchpoints] == [1, 2]


def test_slots_without_watchpoints_are_all_free() -> None:
    """With no watchpoints, every slot is free."""
    slots = Watchpoints(FakeDebugger()).slots()
    assert (slots.used, slots.free, slots.by_kind) == (0, 4, {})


def test_software_watchpoints_do_not_consume_hardware_slots() -> None:
    """Only hardware watchpoints count against the configured limit."""
    debugger = FakeDebugger(
        breakpoints=[
            Breakpoint(1, "watchpoint", 0x06000000, None, True, True),
            Breakpoint(2, "watchpoint", 0x06000004, None, True, False),
        ]
    )
    slots = Watchpoints(debugger).slots()
    assert (slots.used, slots.free) == (1, 3)
    assert [bp.number for bp in slots.software] == [2]
