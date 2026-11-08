"""Control tools: status and atomic frame-step capture (no emulator)."""
import pytest

import re_mcp.tools.control as control


class Recorder:
    """Records (method, params, timeout) and returns a canned result per method."""

    def __init__(self, results: dict[str, dict] | None = None) -> None:
        self.calls: list[tuple[str, dict | None, float | None]] = []
        self.results = results or {}

    def __call__(self, method: str, params: dict | None = None, timeout: float | None = None) -> dict:
        self.calls.append((method, params, timeout))
        return self.results.get(method, {"ok": True})


def test_emu_status(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"emu.status": {"halted": True, "frame": 7}})
    monkeypatch.setattr(control, "control_call", rec)
    out = control.emu_status()
    assert out["halted"] is True and out["frame"] == 7
    assert rec.calls[0][0] == "emu.status"


def test_step_frame_sends_snapshot_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"emu.step_frame": {"ok": True, "frames": 3, "snapshot_frame": 10}})
    monkeypatch.setattr(control, "control_call", rec)
    out = control.emu_step_frame(3, snapshot=True)
    assert out["snapshot_frame"] == 10
    method, params, timeout = rec.calls[0]
    assert method == "emu.step_frame"
    assert params == {"n": 3, "snapshot": True}
    assert timeout is not None and timeout >= 10.0


def test_step_frame_without_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder()
    monkeypatch.setattr(control, "control_call", rec)
    control.emu_step_frame(1)
    assert rec.calls[0][1] == {"n": 1, "snapshot": False}


def test_savestate_save_named(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"savestate.save": {"ok": True, "verified": True}})
    monkeypatch.setattr(control, "control_call", rec)
    out = control.savestate_save(name="twilight", label="sign", owner="s1")
    assert out["verified"] is True
    method, params, timeout = rec.calls[0]
    assert method == "savestate.save"
    assert params == {"name": "twilight", "label": "sign", "owner": "s1"}
    assert timeout is not None


def test_savestate_load_named_force(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"savestate.load": {"ok": True, "verified": True}})
    monkeypatch.setattr(control, "control_call", rec)
    control.savestate_load(name="twilight", owner="s1", force=True)
    assert rec.calls[0][1] == {"name": "twilight", "owner": "s1", "force": True}


def test_savestate_load_state_error_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"savestate.load": {"error": "savestate gamecode differs from the loaded ROM"}})
    monkeypatch.setattr(control, "control_call", rec)
    out = control.savestate_load(3)
    assert "error" in out and "outro jogo" in out["hint"]


def test_savestate_list(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"savestate.list": {"count": 1, "states": []}})
    monkeypatch.setattr(control, "control_call", rec)
    assert control.savestate_list()["count"] == 1
    assert rec.calls[0][0] == "savestate.list"
