"""2.2 helpers: args_on_hit, field_xref and struct_candidate."""
import struct
from typing import cast

import pytest

from re_mcp.application.args import ArgsOnHit
from re_mcp.application.ports import Debugger
from re_mcp.domain.debug import ArgHit
from re_mcp.domain.structs import render_struct, scan_struct_accesses
from re_mcp.domain.symbols import Symbol, SymbolTable
from re_mcp.tools import re as re_tools


def test_scan_struct_accesses_and_render() -> None:
    """Loads/stores become candidate fields with widths and padding."""
    code = bytes.fromhex("100091e50420d3e5084085e5bc60c7e1")
    fields = scan_struct_accesses(code, 0x02000000)
    assert [(field.offset, field.width, field.registers) for field in fields] == [
        (0x04, 1, ("r3",)),
        (0x08, 4, ("r5",)),
        (0x0C, 2, ("r7",)),
        (0x10, 4, ("r1",)),
    ]
    c = render_struct(fields)
    assert "uint8_t field_0x04;" in c
    assert "uint8_t pad_0x05[0x3];" in c
    assert "uint32_t field_0x08;" in c
    assert "uint16_t field_0x0c;" in c


class FakeDebugger:
    """Debugger fake for args/field tests."""

    def __init__(self, continue_ok: bool = True, pc: int = 0x020A11C4) -> None:
        self.continue_ok = continue_ok
        self.pc = pc
        self.removed: list[int] = []
        self.sets: list[tuple[int, str | None]] = []
        self.continue_calls = 0
        self.code = bytes.fromhex("100091e50420d3e5084085e5bc60c7e1")

    def is_running(self) -> bool:
        return False

    def interrupt(self) -> None: ...

    def set_breakpoint(self, addr: int, condition: str | None = None, commands: list[str] | None = None) -> int:
        self.sets.append((addr, condition))
        return 7

    def set_watchpoint(self, addr: int, kind: str, condition: str | None = None) -> int:
        self.sets.append((addr, condition))
        return 8

    def continue_(self, timeout: float = 30.0) -> bool:
        self.continue_calls += 1
        return self.continue_ok

    def read_register(self, name: str) -> int:
        if name == "pc":
            return self.pc
        if name == "sp":
            return 0x023FF000
        if name == "lr":
            return 0x02000010
        if name == "cpsr":
            return 0x60000013
        return {"r0": 2, "r1": 0x02200000, "r2": 1, "r3": 0}.get(name, 0)

    def read_memory(self, addr: int, size: int) -> bytes:
        if addr == 0x023FF000:
            return struct.pack("<8I", *range(8))
        return self.code[:size]

    def remove(self, number: int) -> None:
        self.removed.append(number)


class FakeBridge:
    def __init__(self, debugger: FakeDebugger, table: SymbolTable | None = None) -> None:
        self._debugger = debugger
        self.table = table or SymbolTable([])

    def debugger(self) -> FakeDebugger:
        return self._debugger

    def symbols(self) -> SymbolTable:
        return self.table


def test_args_on_hit_checks_schema() -> None:
    """Valid schema checks are all ok; a bad pointer is reported."""
    debugger = FakeDebugger()
    hit = ArgsOnHit(cast(Debugger, debugger)).collect(
        0x020A11C4,
        schema={"r0": 2, "r1": "ptr", "r2": "nonzero", "r3": "zero", "stack0": 0},
    )[0]
    assert hit.ok is True
    assert debugger.removed == [7]

    bad = FakeDebugger()
    bad.read_register = lambda name: 0x9 if name == "r1" else FakeDebugger().read_register(name)
    hit = ArgsOnHit(cast(Debugger, bad)).collect(0x020A11C4, schema={"r1": "ptr"})[0]
    assert hit.ok is False
    assert hit.checks[0].actual == 0x9


def test_args_on_hit_count_and_timeout() -> None:
    """Count captures N hits; timeout returns none; breakpoint is removed."""
    debugger = FakeDebugger()
    hits = ArgsOnHit(cast(Debugger, debugger)).collect(0x020A11C4, count=2)
    assert len(hits) == 2
    assert debugger.continue_calls == 2
    assert debugger.removed == [7]

    timeout = FakeDebugger(continue_ok=False)
    assert ArgsOnHit(cast(Debugger, timeout)).collect(0x020A11C4) == []
    assert timeout.removed == [7]


def test_args_on_hit_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool annotates the hit PC with a symbol."""
    debugger = FakeDebugger()
    table = SymbolTable([Symbol(0x020A11C4, "callsite")])
    monkeypatch.setattr(re_tools, "bridge", FakeBridge(debugger, table))
    out = re_tools.args_on_hit(0x020A11C4, schema={"r0": 2})
    assert out["count"] == 1
    assert out["hits"][0]["pc_symbol"] == "callsite"
    assert out["hits"][0]["checks"][0]["ok"] is True


def test_field_xref_by_symbol_and_writers(monkeypatch: pytest.MonkeyPatch) -> None:
    """field_xref resolves a symbol base and returns the writer PC."""
    debugger = FakeDebugger()
    table = SymbolTable([
        Symbol(0x02200000, "player"),
        Symbol(0x020A11C4, "writer"),
    ])
    monkeypatch.setattr(re_tools, "bridge", FakeBridge(debugger, table))
    out = re_tools.field_xref("player", 0x10)
    assert out["field"] == "0x02200010"
    assert out["base_symbol"] == "player"
    assert out["hit"]["pc_symbol"] == "writer"
    out = re_tools.field_writers("player", 0x10)
    assert out["kind"] == "write"


def test_struct_candidate_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool reads code and returns fields plus a C skeleton."""
    debugger = FakeDebugger()
    monkeypatch.setattr(re_tools, "bridge", FakeBridge(debugger))
    out = re_tools.struct_candidate(0x02000000, size=16)
    assert [field["offset"] for field in out["fields"]] == [0x04, 0x08, 0x0C, 0x10]
    assert "struct candidate" in out["c"]
