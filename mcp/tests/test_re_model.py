"""Symbols, annotations and decomp snippets (tool-level, fake backends)."""
from pathlib import Path

import pytest

from re_mcp.application.decomp import DecompSnippets
from re_mcp.domain.debug import StackFrame
from re_mcp.domain.symbols import Symbol, SymbolTable
from re_mcp.tools import debug as debug_tools
from re_mcp.tools import re as re_tools


class FakeStore:
    """In-memory FileStore."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}

    def write_bytes(self, name: str, data: bytes) -> str:
        self.files[name] = data.decode("latin-1")
        return f"/out/{name}"

    def write_text(self, name: str, text: str) -> str:
        self.files[name] = text
        return f"/out/{name}"

    def read_bytes(self, name: str) -> bytes | None:
        data = self.files.get(name)
        return data.encode("latin-1") if data is not None else None

    def read_text(self, name: str) -> str | None:
        return self.files.get(name)


class FakeDebugger:
    """Minimal debugger for annotation/hit tests."""

    def __init__(self) -> None:
        self.pc = 0x020A11C4

    def set_watchpoint(self, addr: int, kind: str, condition: str | None = None) -> int:
        return 7

    def continue_(self, timeout: float = 30.0) -> bool:
        return True

    def read_register(self, name: str) -> int:
        return self.pc if name == "pc" else 0

    def remove(self, number: int) -> None: ...

    def read_memory(self, addr: int, size: int) -> bytes:
        return b"\x00\x00\xa0\xe1" * (size // 4)

    def backtrace(self) -> list[StackFrame]:
        return [
            StackFrame(index, 0x020A1100 + index * 4, None)
            for index in range(4)
        ]


class FakeOverlays:
    def overlay_for_address(self, addr: int, core: str = "arm9") -> None:
        return None


class FakeBridge:
    """Minimal bridge with the pieces used by the tools."""

    def __init__(self) -> None:
        self.store = FakeStore()
        self.table = SymbolTable([])
        self.debugger_instance = FakeDebugger()
        self.decomp_instance = DecompSnippets(self.store)

    def symbols(self) -> SymbolTable:
        return self.table

    def add_symbol(self, symbol: Symbol) -> str:
        self.table.add(symbol)
        return self.save_symbols()

    def save_symbols(self) -> str:
        return self.store.write_text("symbols.json", self.table.to_json())

    def set_symbols(self, table: SymbolTable) -> None:
        self.table = table

    def decomp(self) -> DecompSnippets:
        return self.decomp_instance

    def debugger(self) -> FakeDebugger:
        return self.debugger_instance

    def overlays(self) -> FakeOverlays:
        return FakeOverlays()

    def files(self) -> FakeStore:
        return self.store


def test_symbol_define_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    """`symbol_define` adds the symbol and writes symbols.json."""
    bridge = FakeBridge()
    monkeypatch.setattr(re_tools, "bridge", bridge)
    out = re_tools.symbol_define(0x020A11C4, "desenha_painel", "function", "panel", 22)
    assert out["ok"] is True and out["count"] == 1
    assert "desenha_painel" in bridge.store.files["symbols.json"]
    saved = bridge.table.resolve(0x020A11C4)
    assert saved is not None and saved.overlay == 22


def test_symbol_load_merges_and_lists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`symbol_load` merges a .map with existing aliases and lists both."""
    bridge = FakeBridge()
    bridge.table.add(Symbol(0x020A11C4, "alias"))
    monkeypatch.setattr(re_tools, "bridge", bridge)
    map_path = tmp_path / "test.map"
    map_path.write_text("0x02000000 main\n", encoding="utf-8")
    out = re_tools.symbol_load(str(map_path))
    assert out["ok"] is True and out["count"] == 2
    listed = re_tools.symbol_list()
    assert {item["name"] for item in listed["symbols"]} == {"alias", "main"}


def test_disassemble_annotates_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    """`disassemble` annotates the instruction symbol and branch target."""
    bridge = FakeBridge()
    bridge.table.add(Symbol(0x02000000, "foo", "function"))
    bridge.table.add(Symbol(0x02000004, "bar", "function"))
    bridge.table.add(Symbol(0x0200000C, "target", "function"))
    monkeypatch.setattr(debug_tools, "bridge", bridge)
    # mov r0, r0 ; bl #0 (ARM)
    bridge.debugger_instance.read_memory = lambda addr, size: (
        b"\x00\x00\xa0\xe1" + b"\x00\x00\x00\xeb" + b"\x00" * 8
    )[:size]
    out = debug_tools.disassemble(0x02000000, count=2)
    assert out["instructions"][0]["symbol"] == "foo"
    assert out["instructions"][1]["symbol"] == "bar"
    assert out["instructions"][1]["target_symbol"] == "target"


def test_backtrace_annotates_function(monkeypatch: pytest.MonkeyPatch) -> None:
    """`debug_backtrace` fills function from symbols when gdb gives null."""
    bridge = FakeBridge()
    bridge.table.add(Symbol(0x020A1100, "func0"))
    monkeypatch.setattr(debug_tools, "bridge", bridge)
    out = debug_tools.debug_backtrace()
    assert out["frames"][0]["function"] == "func0"
    assert out["frames"][0]["symbol"] == "func0"


def test_find_writer_annotates_pc(monkeypatch: pytest.MonkeyPatch) -> None:
    """`find_writer` includes the symbol at the hit PC."""
    bridge = FakeBridge()
    bridge.table.add(Symbol(0x020A11C4, "writer"))
    monkeypatch.setattr(re_tools, "bridge", bridge)
    out = re_tools.find_writer(0x0222A1F0)
    assert out["hit"]["pc_symbol"] == "writer"


def test_addr_valid_annotates_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    """`addr_valid` includes the symbol at the address."""
    bridge = FakeBridge()
    bridge.table.add(Symbol(0x020A2D90, "here"))
    monkeypatch.setattr(re_tools, "bridge", bridge)
    out = re_tools.addr_valid("0x020A2D90")
    assert out["symbol"] == "here"


def test_decomp_snippet_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    """`decomp_snippet` stores and reloads C+ASM."""
    bridge = FakeBridge()
    monkeypatch.setattr(re_tools, "bridge", bridge)
    out = re_tools.decomp_snippet(0x020A11C4, c="void f() {}", asm="push {lr}")
    assert out["ok"] is True and out["c"] == "void f() {}"
    assert "decomp.json" in bridge.store.files
    again = re_tools.decomp_snippet(0x020A11C4)
    assert again["asm"] == "push {lr}"


def test_bridge_symbols_persist_across_instances(tmp_path: Path) -> None:
    """The real Bridge reloads symbols.json on a new instance."""
    from re_mcp.bridge import Bridge
    from re_mcp.config import Config

    config = Config(
        control_socket="",
        gdb_path="",
        arm9_port=0,
        arm7_port=0,
        out_dir=str(tmp_path),
    )
    first = Bridge(config)
    first.add_symbol(Symbol(0x020A11C4, "desenha_painel", "function", "panel", 22))
    second = Bridge(config)
    restored = second.symbols().resolve(0x020A11C4)
    assert restored is not None
    assert (restored.name, restored.kind, restored.comment, restored.overlay) == (
        "desenha_painel", "function", "panel", 22,
    )
