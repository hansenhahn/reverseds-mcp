"""Backtrace fallback tests: pure stack scan + application service."""
import struct
from typing import cast

from re_mcp.application.backtrace import Backtrace
from re_mcp.application.ports import Debugger
from re_mcp.domain.backtrace import StackScanner
from re_mcp.domain.debug import StackFrame


def _stack(*words: int) -> bytes:
    return b"".join(struct.pack("<I", word) for word in words)


def test_scan_accepts_even_code_addresses_and_dedupes() -> None:
    """ARM/Thumb candidates (even, in code) are kept; odd/unmapped/dupes are not."""
    stack = _stack(
        0x02001000,
        0x02001002,
        0x01000000,
        0x02001000,
        0x02002000,
        0x02003001,
        0xFFFF0010,
    )
    assert StackScanner().scan(stack) == (
        0x02001000,
        0x02001002,
        0x02002000,
        0xFFFF0010,
    )


def test_scan_skips_excluded_and_stack_range() -> None:
    """Current PC, known frames and the stack range itself are skipped."""
    stack = _stack(0x02001000, 0x02002000, 0x02003000)
    assert StackScanner(
        exclude={0x02001000},
        exclude_range=(0x02002000, 0x02002004),
    ).scan(stack) == (0x02003000,)


def test_scan_respects_limit() -> None:
    """The candidate list is capped."""
    stack = _stack(0x02001000, 0x02001004, 0x02001008)
    assert StackScanner(limit=2).scan(stack) == (0x02001000, 0x02001004)


class FakeBacktraceDebugger:
    """Fake debugger with configurable frames, registers and stack."""

    def __init__(
        self,
        frames: list[StackFrame],
        stack: bytes = b"",
        code: dict[int, bytes] | None = None,
        read_error: bool = False,
    ) -> None:
        self._frames = frames
        self._stack = stack
        self._code = code or {}
        self._read_error = read_error
        self.read_calls = 0

    def backtrace(self) -> list[StackFrame]:
        return self._frames

    def refresh_registers(self) -> None: ...
    def read_register(self, name: str) -> int:
        return 0x02001000 if name == "pc" else 0x023FF000

    def read_memory(self, addr: int, size: int) -> bytes:
        self.read_calls += 1
        if self._read_error:
            raise RuntimeError("stack unreadable")
        if addr == 0x023FF000:
            return self._stack
        return self._code.get(addr, b"\x00" * size)


def test_backtrace_appends_stack_candidates() -> None:
    """A short gdb backtrace is completed from the stack with source='stack'."""
    debugger = FakeBacktraceDebugger(
        frames=[
            StackFrame(0, 0x02001100, "inner"),
            StackFrame(1, 0x02001200, "outer"),
        ],
        stack=_stack(0x02001100, 0x02001300, 0x02001400),
        code={
            0x020012FC: bytes.fromhex("000000eb"),
            0x020013FC: bytes.fromhex("000000eb"),
        },
    )
    frames = Backtrace(cast(Debugger, debugger)).frames()
    assert [(frame.index, frame.pc, frame.source) for frame in frames] == [
        (0, 0x02001100, "gdb"),
        (1, 0x02001200, "gdb"),
        (2, 0x02001300, "stack"),
        (3, 0x02001400, "stack"),
    ]


def test_backtrace_drops_candidates_without_a_call() -> None:
    """A stack word without a preceding BL/BLX is not a return address."""
    debugger = FakeBacktraceDebugger(
        frames=[StackFrame(0, 0x02001100, "inner")],
        stack=_stack(0x02001300, 0x02001400),
        code={0x020012FC: bytes.fromhex("000000eb")},
    )
    frames = Backtrace(cast(Debugger, debugger)).frames()
    assert [(frame.pc, frame.source) for frame in frames] == [
        (0x02001100, "gdb"),
        (0x02001300, "stack"),
    ]


def test_backtrace_skips_scan_when_gdb_has_enough_frames() -> None:
    """Four or more gdb frames do not trigger a stack read."""
    debugger = FakeBacktraceDebugger(
        frames=[StackFrame(index, 0x02001000 + index * 4, None) for index in range(4)]
    )
    frames = Backtrace(cast(Debugger, debugger)).frames()
    assert debugger.read_calls == 0
    assert all(frame.source == "gdb" for frame in frames)


def test_backtrace_returns_gdb_frames_when_stack_read_fails() -> None:
    """A failed stack read keeps the gdb frames instead of raising."""
    debugger = FakeBacktraceDebugger(
        frames=[StackFrame(0, 0x02001100, "inner")],
        read_error=True,
    )
    frames = Backtrace(cast(Debugger, debugger)).frames()
    assert [(frame.pc, frame.source) for frame in frames] == [(0x02001100, "gdb")]
