"""Tool-level tests for Wave 0 (slots, addr_valid, normalized echo)."""
import pytest

from re_mcp.domain.debug import Breakpoint
from re_mcp.domain.overlays import Overlay, OverlayHit
from re_mcp.infra.ndsrom import NdsRomError
from re_mcp.tools import debug as debug_tools
from re_mcp.tools import re as re_tools


class FakeDebugger:
    """Minimal debugger for the tools under test."""

    def __init__(self, breakpoints: list[Breakpoint] | None = None) -> None:
        self._breakpoints = breakpoints or []
        self.written: tuple[int, bytes] | None = None
        self.breakpoint_args: tuple[int, str | None, list[str] | None] | None = None

    def core(self) -> str | None:
        return "arm9"

    def watchpoint_limit(self) -> int:
        return 4

    def breakpoints(self) -> list[Breakpoint]:
        return self._breakpoints

    def set_breakpoint(
        self, addr: int, condition: str | None = None, commands: list[str] | None = None
    ) -> int:
        self.breakpoint_args = (addr, condition, commands)
        return 11

    def write_memory(self, addr: int, data: bytes) -> None:
        self.written = (addr, data)


class FakeOverlays:
    """Returns a fixed overlay hit."""

    def __init__(self, hit: OverlayHit | None) -> None:
        self._hit = hit

    def overlay_for_address(self, addr: int, core: str = "arm9") -> OverlayHit | None:
        return self._hit


class FakeBridge:
    """Minimal bridge for tool tests."""

    def __init__(
        self,
        debugger: FakeDebugger | None = None,
        overlays: FakeOverlays | None = None,
        rom_error: bool = False,
    ) -> None:
        self._debugger = debugger or FakeDebugger()
        self._overlays = overlays or FakeOverlays(None)
        self._rom_error = rom_error

    def debugger(self) -> FakeDebugger:
        return self._debugger

    def overlays(self) -> FakeOverlays:
        if self._rom_error:
            raise NdsRomError("nenhuma ROM carregada no emulador")
        return self._overlays


def test_debug_slots_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """`debug_slots` reports limit/used/free and the watchpoint list."""
    debugger = FakeDebugger(
        breakpoints=[
            Breakpoint(1, "watchpoint", 0x06000000, None, True),
            Breakpoint(2, "read-watchpoint", 0x06000004, "r0 == 1", True),
            Breakpoint(3, "breakpoint", 0x02000000, None, True),
        ]
    )
    monkeypatch.setattr(debug_tools, "bridge", FakeBridge(debugger=debugger))
    out = debug_tools.debug_slots()
    assert (out["core"], out["watchpoint_limit"], out["watchpoints_used"], out["free"]) == (
        "arm9",
        4,
        2,
        2,
    )
    assert out["by_kind"] == {"watchpoint": 1, "read-watchpoint": 1}
    assert [bp["number"] for bp in out["watchpoints"]] == [1, 2]


def test_addr_valid_main_ram_without_rom(monkeypatch: pytest.MonkeyPatch) -> None:
    """A main-RAM address is valid and works without a loaded ROM."""
    monkeypatch.setattr(re_tools, "bridge", FakeBridge(rom_error=True))
    out = re_tools.addr_valid("0x020A2D90")
    assert out["value_dec"] == 0x020A2D90
    assert out["value_hex"] == "0x020a2d90"
    assert out["aligned4"] is True
    assert out["mapped"] is True
    assert out["region"] == "main-ram"
    assert out["overlay"] is None


def test_addr_valid_resolves_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    """An address inside an overlay includes its id/base and offset."""
    overlay = Overlay(
        core="arm9",
        index=22,
        ram_address=0x02082960,
        ram_size=0x20000,
        bss_size=0,
        file_id=123,
    )
    hit = OverlayHit(overlay, 0x1E864)
    monkeypatch.setattr(re_tools, "bridge", FakeBridge(overlays=FakeOverlays(hit)))
    out = re_tools.addr_valid(0x020A11C4)
    assert out["region"] == "main-ram"
    assert out["overlay"] == {
        "core": "arm9",
        "index": 22,
        "ram_address": 0x02082960,
        "ram_size": 0x20000,
        "bss_size": 0,
        "file_id": 123,
        "offset": 0x1E864,
    }


def test_addr_valid_unmapped_is_not_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unknown region returns mapped=False instead of an error."""
    monkeypatch.setattr(re_tools, "bridge", FakeBridge(rom_error=True))
    out = re_tools.addr_valid(0x01000000)
    assert out["mapped"] is False
    assert out["region"] is None


def test_addr_valid_invalid_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid input returns the standard error with a hint."""
    monkeypatch.setattr(re_tools, "bridge", FakeBridge())
    out = re_tools.addr_valid("zzz")
    assert "error" in out
    assert "hint" in out


def test_set_breakpoint_echoes_normalized_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`set_breakpoint` includes the normalized address in the result."""
    monkeypatch.setattr(debug_tools, "bridge", FakeBridge())
    out = debug_tools.set_breakpoint(0x020A2D90)
    assert out == {
        "number": 11,
        "addr": "0x020a2d90",
        "condition": None,
        "commands": [],
    }


def test_set_breakpoint_passes_condition_and_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`set_breakpoint` forwards condition and commands to the backend."""
    debugger = FakeDebugger()
    monkeypatch.setattr(debug_tools, "bridge", FakeBridge(debugger=debugger))
    out = debug_tools.set_breakpoint(
        0x020A1394, condition="$r0 == 2", commands=["silent", "continue"]
    )
    assert out["condition"] == "$r0 == 2"
    assert out["commands"] == ["silent", "continue"]
    assert debugger.breakpoint_args == (
        0x020A1394,
        "$r0 == 2",
        ["silent", "continue"],
    )


def test_mem_write_echoes_address_and_size(monkeypatch: pytest.MonkeyPatch) -> None:
    """`mem_write` echoes the address and byte count."""
    debugger = FakeDebugger()
    monkeypatch.setattr(debug_tools, "bridge", FakeBridge(debugger=debugger))
    out = debug_tools.mem_write(0x0222A1F0, "deadbeef")
    assert out == {"ok": True, "addr": "0x0222a1f0", "size": 4}
    assert debugger.written == (0x0222A1F0, bytes.fromhex("deadbeef"))


def test_debug_error_hints_on_hardware_resource_exhaustion() -> None:
    """A hardware-resource failure points the agent at the slot diagnostics."""
    from re_mcp.infra.gdb import DebugError
    from re_mcp.tools.app import debug_error

    out = debug_error(DebugError("Cannot insert hardware watchpoint 5."))
    assert "hint" in out and "debug_slots" in out["hint"]


def test_debug_error_hints_on_missing_breakpoint() -> None:
    """Removing an unknown number points the agent at the listing tools."""
    from re_mcp.infra.gdb import DebugError
    from re_mcp.tools.app import debug_error

    out = debug_error(DebugError("breakpoint/watchpoint 99 não existe"))
    assert "hint" in out and "list_breakpoints" in out["hint"]
