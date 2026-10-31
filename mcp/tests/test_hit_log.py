"""Hit-log and cold-reset MCP tools (fake control channel)."""
import pytest

from re_mcp.tools import control as control_tools
from re_mcp.tools import debug as debug_tools


def test_emu_reset_calls_control(monkeypatch: pytest.MonkeyPatch) -> None:
    """`emu_reset` forwards to the control channel."""
    calls: list[tuple[str, dict | None, float | None]] = []

    def fake(method: str, params: dict | None = None, timeout: float | None = None) -> dict:
        calls.append((method, params, timeout))
        return {"ok": True}

    monkeypatch.setattr(control_tools, "control_call", fake)
    assert control_tools.emu_reset() == {"ok": True}
    assert calls == [("emu.reset", None, 30.0)]


def test_hit_log_start_stop_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    """The lifecycle tools pass the core/capacity to the control channel."""
    calls: list[tuple[str, dict | None]] = []

    def fake(method: str, params: dict | None = None, timeout: float | None = None) -> dict:
        calls.append((method, params))
        return {"ok": True}

    monkeypatch.setattr(debug_tools, "control_call", fake)
    assert debug_tools.hit_log_start("arm7", 128) == {"ok": True}
    assert debug_tools.hit_log_stop("arm7") == {"ok": True}
    assert debug_tools.hit_log_clear("arm7") == {"ok": True}
    assert calls == [
        ("gdb.hits.start", {"core": "arm7", "capacity": 128}),
        ("gdb.hits.stop", {"core": "arm7"}),
        ("gdb.hits.clear", {"core": "arm7"}),
    ]


def test_hit_log_read_formats_and_clears(monkeypatch: pytest.MonkeyPatch) -> None:
    """`hit_log_read` formats addresses and clears after a successful read."""
    calls: list[str] = []

    def fake(method: str, params: dict | None = None, timeout: float | None = None) -> dict:
        calls.append(method)
        if method == "gdb.hits.read":
            return {
                "count": 1,
                "dropped": 2,
                "hits": [
                    {"pc": 0x02001100, "addr": 0x06000000, "kind": "write"}
                ],
            }
        return {"ok": True}

    monkeypatch.setattr(debug_tools, "control_call", fake)
    out = debug_tools.hit_log_read("arm9", clear=True)
    assert out == {
        "count": 1,
        "dropped": 2,
        "hits": [{"pc": "0x02001100", "addr": "0x06000000", "kind": "write"}],
    }
    assert calls == ["gdb.hits.read", "gdb.hits.clear"]


def test_hit_log_read_error_does_not_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed read does not clear the log."""
    calls: list[str] = []

    def fake(method: str, params: dict | None = None, timeout: float | None = None) -> dict:
        calls.append(method)
        return {"error": "nope", "hint": "..."}

    monkeypatch.setattr(debug_tools, "control_call", fake)
    out = debug_tools.hit_log_read("arm9", clear=True)
    assert out["error"] == "nope"
    assert calls == ["gdb.hits.read"]


def test_emu_reset_refreshes_gdb_register_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """`emu_reset` flushes gdb's register cache when the debugger is connected."""
    refreshed: list[bool] = []

    class FakeDebugger:
        def core(self) -> str:
            return "arm9"

        def refresh_registers(self) -> None:
            refreshed.append(True)

    class FakeBridge:
        def debugger(self) -> FakeDebugger:
            return FakeDebugger()

    def fake_call(method: str, params: dict | None = None, timeout: float | None = None) -> dict:
        return {"ok": True}

    monkeypatch.setattr(control_tools, "bridge", FakeBridge())
    monkeypatch.setattr(control_tools, "control_call", fake_call)
    assert control_tools.emu_reset() == {"ok": True}
    assert refreshed == [True]
