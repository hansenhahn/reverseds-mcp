"""2.5: contract checks (args/return) and patch equivalence."""
import struct
from typing import cast

import pytest

from re_mcp.application.contract import ContractChecks
from re_mcp.application.ports import Debugger
from re_mcp.domain.contract import ArgSpec, Contract
from re_mcp.domain.patch import Patch, PatchDiff
from re_mcp.domain.symbols import Symbol, SymbolTable
from re_mcp.tools import re as re_tools


class FakeDebugger:
    """Debugger fake for contract and patch tests."""

    def __init__(
        self,
        continue_results: list[bool] | None = None,
        lr: int = 0x02000010,
        memory: bytes = b"\x00\x00\x00\x00",
    ) -> None:
        self.continue_results = list(continue_results or [True])
        self.lr = lr
        self.memory = memory
        self.sets: list[int] = []
        self.removed: list[int] = []

    def is_running(self) -> bool:
        return False

    def interrupt(self) -> None: ...

    def set_breakpoint(
        self,
        addr: int,
        condition: str | None = None,
        commands: list[str] | None = None,
    ) -> int:
        self.sets.append(addr)
        return len(self.sets)

    def continue_(self, timeout: float = 30.0) -> bool:
        return self.continue_results.pop(0) if self.continue_results else False

    def read_register(self, name: str) -> int:
        if name == "pc":
            return 0x020A11C4
        if name == "sp":
            return 0x023FF000
        if name == "lr":
            return self.lr
        if name == "cpsr":
            return 0x60000013
        return {"r0": 2, "r1": 0x02200000, "r2": 1, "r3": 0}.get(name, 0)

    def read_memory(self, addr: int, size: int) -> bytes:
        if addr == 0x023FF000:
            return struct.pack("<8I", *range(8))
        if addr == 0x02000000:
            return self.memory[:size].ljust(size, b"\x00")
        return b"\x00" * size

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


def test_arg_spec_tokens_and_checked() -> None:
    """Known tokens check values; unknown tokens stay unchecked."""
    assert ArgSpec("r0", "int:2").matches(2)
    assert ArgSpec("r0", "hex:0x10").matches(0x10)
    assert ArgSpec("r0", "range:1:3").matches(2)
    assert ArgSpec("r0", "mask:0xf0:0x20").matches(0x2A)
    assert ArgSpec("r0", "ptr").matches(0x02200000)
    assert ArgSpec("r0", "zero").matches(0)
    assert ArgSpec("r0", "nonzero").matches(1)
    assert ArgSpec("r0", "banana").matches(0xDEAD) is True
    assert ArgSpec("r0", "banana").checked is False


def test_contract_checks_args_and_stack() -> None:
    """The contract resolves registers and stack words."""
    contract = Contract.from_schema({"r0": 2, "stack0": 0})
    checks = contract.check_args(
        {"r0": 2}, (0, 1)
    )
    assert [check.ok for check in checks] == [True, True]
    assert checks[0].checked is True
    assert ArgSpec("r9", "int:1").checked is True


def test_contract_checks_return() -> None:
    """Return checks use the return registers."""
    contract = Contract.from_schema({"r0": 2}, {"r0": "zero"})
    assert contract.returns_expected is True
    checks = contract.check_returns({"r0": 1})
    assert checks[0].ok is False


def test_contract_capture_and_return() -> None:
    """A successful call captures args and the first return."""
    debugger = FakeDebugger(continue_results=[True, True])
    contract = Contract.from_schema({"r0": 2}, {"r0": 2})
    hits = ContractChecks(cast(Debugger, debugger)).run(0x020A11C4, contract)
    assert len(hits) == 1
    assert hits[0].ok is True
    assert hits[0].returned is not None
    assert debugger.sets == [0x020A11C4, 0x02000010]
    assert debugger.removed == [1, 2]


def test_contract_return_timeout() -> None:
    """A missing return is reported, and the temporary breakpoints are removed."""
    debugger = FakeDebugger(continue_results=[True, False])
    contract = Contract.from_schema({"r0": 2}, {"r0": 2})
    hits = ContractChecks(cast(Debugger, debugger)).run(0x020A11C4, contract)
    assert hits[0].returned is None
    assert hits[0].ok is False
    assert debugger.removed == [1, 2]


def test_contract_check_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool reports hits, divergences and the callsite symbol."""
    debugger = FakeDebugger(continue_results=[True, True])
    table = SymbolTable([Symbol(0x020A11C4, "callsite")])
    monkeypatch.setattr(re_tools, "bridge", FakeBridge(debugger, table))
    out = re_tools.contract_check(
        0x020A11C4, {"r0": 2}, {"r0": 2}
    )
    assert out["ok"] is True
    assert out["callsite_symbol"] == "callsite"
    assert out["count"] == 1
    assert out["hits"][0]["return"]["ok"] is True

    bad = FakeDebugger(continue_results=[True, True])
    bad.read_register = lambda name: 9 if name == "r1" else FakeDebugger().read_register(name)  # type: ignore[method-assign]
    monkeypatch.setattr(re_tools, "bridge", FakeBridge(bad))
    out = re_tools.contract_check(0x020A11C4, {"r1": "ptr"})
    assert out["ok"] is False
    assert out["divergences"][0]["kind"] == "arg"
    assert out["divergences"][0]["actual"] == 9


def test_patch_diff_and_regions() -> None:
    """Identical writes are equal; diverging bytes are listed."""
    memory = {0x02000000 + offset: byte for offset, byte in enumerate(b"\x00" * 4)}
    asm = Patch.from_specs([{"addr": 0x02000000, "bytes": "aabb"}])
    c_equiv = Patch.from_specs([{"addr": 0x02000000, "bytes": "aabb"}])
    assert PatchDiff.between(asm, c_equiv, memory).iguais is True
    assert Patch.merged_regions(asm, c_equiv) == ((0x02000000, 0x02000002),)

    other = Patch.from_specs([{"addr": 0x02000000, "bytes": "aabc"}])
    diff = PatchDiff.between(asm, other, memory)
    assert diff.iguais is False
    assert [(item.addr, item.asm, item.c) for item in diff.diffs] == [
        (0x02000001, 0xBB, 0xBC)
    ]


def test_patch_overlap_last_write_wins() -> None:
    """Overlapping writes use the last value in the patch order."""
    memory = {0x02000000: 0}
    patch = Patch.from_specs(
        [
            {"addr": 0x02000000, "bytes": "0102"},
            {"addr": 0x02000001, "bytes": "03"},
        ]
    )
    assert patch.apply(memory)[0x02000000] == 1
    assert patch.apply(memory)[0x02000001] == 3


def test_diff_patch_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool reads current memory and serializes the byte diff."""
    debugger = FakeDebugger(memory=b"\x00\x00\x00\x00")
    monkeypatch.setattr(re_tools, "bridge", FakeBridge(debugger))
    out = re_tools.diff_patch(
        [{"addr": 0x02000000, "bytes": "aabb"}],
        [{"addr": 0x02000000, "bytes": "aabc"}],
    )
    assert out["mode"] == "static"
    assert out["iguais"] is False
    assert out["diffs"] == [{"addr": "0x02000001", "asm": 0xBB, "c": 0xBC}]
    assert out["regions"] == [{"start": "0x02000000", "end": "0x02000002"}]


def test_diff_patch_tool_rejects_invalid_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    """A spec without bytes fails before touching memory."""
    debugger = FakeDebugger()
    monkeypatch.setattr(re_tools, "bridge", FakeBridge(debugger))
    out = re_tools.diff_patch([{"addr": 0x02000000}], [{"addr": 0x02000000, "bytes": "00"}])
    assert "error" in out
