"""3D tools: call mapping, texture dump and trace helpers (no emulator)."""
import pytest

from re_mcp.tools import three_d


class Recorder:
    """Records (method, params) and returns a canned result per method."""

    def __init__(self, results: dict[str, dict] | None = None) -> None:
        self.calls: list[tuple[str, dict | None, float | None]] = []
        self.results = results or {}

    def __call__(self, method: str, params: dict | None = None, timeout: float | None = None) -> dict:
        self.calls.append((method, params, timeout))
        return self.results.get(method, {"ok": True})


def test_gpu3d_state(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"3d.state": {"frame": 10}})
    monkeypatch.setattr(three_d, "control_call", rec)
    assert three_d.gpu3d_state()["frame"] == 10
    assert rec.calls[0][0] == "3d.state"


def test_gpu3d_polygons_params(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder()
    monkeypatch.setattr(three_d, "control_call", rec)
    three_d.gpu3d_polygons(max_items=8, vertices=False)
    assert rec.calls[0] == ("3d.polygons", {"max_items": 8, "vertices": False}, None)


def test_gpu3d_textures(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"3d.textures": {"count": 2, "textures": []}})
    monkeypatch.setattr(three_d, "control_call", rec)
    assert three_d.gpu3d_textures()["count"] == 2
    assert rec.calls[0][0] == "3d.textures"


def test_texture_dump_by_index(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"3d.texture": {"binary": {"width": 32, "height": 16, "data": b""}}})
    monkeypatch.setattr(three_d, "control_call", rec)
    saved: dict = {}

    def fake_save(result: dict, *, format: str, prefix: str) -> dict:
        saved.update(format=format, prefix=prefix)
        return {"paths": ["/out/texture_2.png"]}

    monkeypatch.setattr(three_d, "save_framebuffer_pngs", fake_save)
    out = three_d.gpu3d_texture_dump(index=2)
    assert out["paths"] == ["/out/texture_2.png"]
    assert out["width"] == 32 and out["height"] == 16
    assert rec.calls[0][0] == "3d.texture"
    assert rec.calls[0][1] == {"index": 2}
    assert saved["prefix"] == "texture_2"


def test_texture_dump_requires_selector(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder()
    monkeypatch.setattr(three_d, "control_call", rec)
    out = three_d.gpu3d_texture_dump()
    assert "error" in out
    assert not rec.calls


def test_texture_dump_explicit_params(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"3d.texture": {"binary": {"width": 8, "height": 8, "data": b""}}})
    monkeypatch.setattr(three_d, "control_call", rec)
    monkeypatch.setattr(
        three_d, "save_framebuffer_pngs", lambda result, *, format, prefix: {"paths": ["x"]}
    )
    three_d.gpu3d_texture_dump(tex_param=0x12345678, tex_palette=3)
    assert rec.calls[0][1] == {"tex_param": 0x12345678, "tex_palette": 3}


def test_snapshot_timeout_adds_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"3d.state": {"error": "3D snapshot timeout (emulator paused?)"}})
    monkeypatch.setattr(three_d, "control_call", rec)
    out = three_d.gpu3d_state()
    assert "error" in out and "hint" in out


def test_gxfifo_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"3d.gxfifo.read": {"count": 0, "commands": []}})
    monkeypatch.setattr(three_d, "control_call", rec)
    slept: list[float] = []
    monkeypatch.setattr(three_d.time, "sleep", lambda s: slept.append(s))

    three_d.gxfifo_trace_start(max_items=16)
    out = three_d.gxfifo_trace_read(seconds=0.5)
    three_d.gxfifo_trace_stop()

    assert [c[0] for c in rec.calls] == [
        "3d.gxfifo.start", "3d.gxfifo.read", "3d.gxfifo.stop"
    ]
    assert rec.calls[0][1] == {"max_items": 16}
    assert slept == [0.5]
    assert out["count"] == 0
