"""Debug service tests (domain, with a fake Debugger)."""
from re_mcp.application.watchpoints import Watchpoints
from re_mcp.domain.debug import MemoryDiff


class FakeDebugger:
    """Fake Debugger that satisfies the `Debugger` port."""

    def __init__(self) -> None:
        self.removed: int | None = None

    def connect(self, core: str) -> None: ...
    def write_register(self, name: str, value: int) -> None: ...
    def read_memory(self, addr: int, size: int) -> bytes:
        return b""
    def write_memory(self, addr: int, data: bytes) -> None: ...
    def set_breakpoint(self, addr: int) -> int:
        return 0
    def step(self) -> None: ...
    def interrupt(self) -> None: ...
    def resume(self) -> None: ...
    def wait_stop(self, timeout: float) -> bool:
        return True
    def is_running(self) -> bool:
        return False
    def disconnect(self) -> None: ...
    def close(self) -> None: ...

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
