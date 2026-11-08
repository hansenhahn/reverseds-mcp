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
    assert rec.calls[0] == (
        "3d.polygons",
        {"max_items": 8, "vertices": False, "source": "auto"},
        None,
    )


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
    assert rec.calls[0][1] == {"index": 2, "source": "auto"}
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
    assert rec.calls[0][1] == {
        "tex_param": 0x12345678,
        "tex_palette": 3,
        "source": "auto",
    }


def test_snapshot_source_param(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"3d.state": {"frame": 42}})
    monkeypatch.setattr(three_d, "control_call", rec)
    assert three_d.gpu3d_state(source="last")["frame"] == 42
    assert rec.calls[0] == ("3d.state", {"source": "last"}, None)


def test_snapshot_timeout_adds_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"3d.state": {"error": "3D snapshot timeout (emulator paused?)"}})
    monkeypatch.setattr(three_d, "control_call", rec)
    out = three_d.gpu3d_state()
    assert "error" in out and "hint" in out


def test_snapshot_no_cache_adds_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"3d.polygons": {"error": "no cached 3D snapshot"}})
    monkeypatch.setattr(three_d, "control_call", rec)
    out = three_d.gpu3d_polygons(source="last")
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


def test_gxfifo_typed_decode(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({
        "3d.gxfifo.read": {
            "count": 2,
            "commands": [
                {"cmd": 0x40, "params": [0], "pc": 0, "frame": 0, "fifo": 0},
                {"cmd": 0x23, "params": [0x00010002, 0x0003], "pc": 0, "frame": 0, "fifo": 0},
            ],
        }
    })
    monkeypatch.setattr(three_d, "control_call", rec)
    out = three_d.gxfifo_trace_read(decode="typed")
    assert out["commands"][0]["typed"]["primitive_name"] == "triangles"
    assert out["commands"][1]["typed"] == {"x": 2, "y": 1, "z": 3}


def test_origin_tools_format_hex(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({
        "origin.query": {"count": 1, "unknown": False,
                         "hits": [{"src": 0x02001000, "dst_lo": 0x06000000,
                                   "dst_hi": 0x06000100, "len": 0x100,
                                   "pc": 0x0200ABCD, "frame": 3, "kind": 0}]}
    })
    monkeypatch.setattr(three_d, "control_call", rec)
    out = three_d.origin_query(0x06000000, 0x100)
    assert out["hits"][0]["src"] == "0x02001000"
    assert out["hits"][0]["pc"] == "0x0200abcd"


def test_find_bytes_in_ram(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(three_d, "control_call", Recorder())
    monkeypatch.setattr(three_d, "_find_pattern", lambda *a: [0x02001234])
    out = three_d.find_bytes_in_ram(hex_data="deadbeef")
    assert out["count"] == 1
    assert out["hits"] == ["0x02001234"]


def test_find_bytes_in_ram_rejects_bad_hex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(three_d, "control_call", Recorder())
    out = three_d.find_bytes_in_ram(hex_data="zz")
    assert "error" in out


def test_texture_source_finds_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({
        "3d.textures": {"textures": [{"index": 0, "tex_param": 0x12345678,
                                      "tex_palette": 0x20, "format": 3,
                                      "width": 8, "height": 8, "vram_addr": 0}]},
        "3d.texture_raw": {"binary": {"width": 8, "height": 8, "data": b"\x01\x02\x03"},
                           "format_id": 3},
    })
    monkeypatch.setattr(three_d, "control_call", rec)
    monkeypatch.setattr(three_d, "_find_pattern", lambda *a: [0x02002000])
    out = three_d.gpu3d_texture_source(index=0)
    assert out["count"] == 1
    assert out["candidates"] == ["0x02002000"]
    assert out["unknown"] is False


def test_texture_source_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({
        "3d.textures": {"textures": [{"index": 0, "tex_param": 0x1, "tex_palette": 0,
                                      "format": 3, "width": 8, "height": 8, "vram_addr": 0}]},
        "3d.texture_raw": {"binary": {"width": 8, "height": 8, "data": b"\xaa"},
                           "format_id": 3},
    })
    monkeypatch.setattr(three_d, "control_call", rec)
    monkeypatch.setattr(three_d, "_find_pattern", lambda *a: [])
    out = three_d.gpu3d_texture_source(index=0)
    assert out["unknown"] is True and out["count"] == 0


def test_gxfifo_source(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = Recorder({"gxfifo.origin": {"count": 1, "unknown": False,
                                      "hits": [{"src": 0x02003000, "len": 0x40}]}})
    monkeypatch.setattr(three_d, "control_call", rec)
    out = three_d.gxfifo_source()
    assert out["count"] == 1
    assert rec.calls[0][0] == "gxfifo.origin"
