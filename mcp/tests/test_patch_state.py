"""Persistent RAM patches (application + tools + savestate integration)."""
import json
from typing import cast

import pytest

from re_mcp.application.patch_state import PatchManager
from re_mcp.application.ports import Debugger, FileStore
from re_mcp.domain.patch import Patch
from re_mcp.tools import control as control_tools
from re_mcp.tools import re as re_tools


class FakeStore:
    def __init__(self) -> None:
        self.files: dict[str, str] = {}

    def write_text(self, name: str, text: str) -> str:
        self.files[name] = text
        return f"/out/{name}"

    def read_text(self, name: str) -> str | None:
        return self.files.get(name)

    def write_bytes(self, name: str, data: bytes) -> str:
        self.files[name] = data.decode("latin-1")
        return f"/out/{name}"

    def read_bytes(self, name: str) -> bytes | None:
        text = self.files.get(name)
        return text.encode("latin-1") if text is not None else None


class FakeDebugger:
    def __init__(self) -> None:
        self.writes: list[tuple[int, bytes]] = []

    def write_memory(self, addr: int, data: bytes) -> None:
        self.writes.append((addr, data))


def test_patch_manager_persists_and_reapplies() -> None:
    """A patch is written, persisted and visible from a fresh manager."""
    store = FakeStore()
    debugger = FakeDebugger()
    manager = PatchManager(cast(Debugger, debugger), cast(FileStore, store))
    patch, path = manager.set([{"addr": 0x02000000, "bytes": "deadbeef"}])
    assert path is not None
    assert debugger.writes == [(0x02000000, b"\xde\xad\xbe\xef")]
    assert (len(patch.writes), patch.writes[0].addr) == (1, 0x02000000)

    again = PatchManager(cast(Debugger, FakeDebugger()), cast(FileStore, store))
    loaded = again.list()
    assert loaded is not None and loaded.to_specs() == [{"addr": 0x02000000, "bytes": "deadbeef"}]

    debugger2 = FakeDebugger()
    manager2 = PatchManager(cast(Debugger, debugger2), cast(FileStore, store))
    assert manager2.apply() == 1
    assert debugger2.writes == [(0x02000000, b"\xde\xad\xbe\xef")]


def test_patch_manager_apply_false_and_clear() -> None:
    """`apply=false` stores without writing; clear empties the file."""
    store = FakeStore()
    debugger = FakeDebugger()
    manager = PatchManager(cast(Debugger, debugger), cast(FileStore, store))
    manager.set([{"addr": 0x02000000, "bytes": "01"}], apply=False)
    assert debugger.writes == []
    assert manager.apply() == 1
    assert manager.clear() == 1
    assert manager.list() is None
    assert json.loads(store.files["patches.json"])["writes"] == []


def test_patch_manager_rejects_invalid_spec() -> None:
    manager = PatchManager(cast(Debugger, FakeDebugger()), cast(FileStore, FakeStore()))
    with pytest.raises(ValueError):
        manager.set([{"addr": 0x02000000}])


def test_patch_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    store = FakeStore()
    debugger = FakeDebugger()
    manager = PatchManager(cast(Debugger, debugger), cast(FileStore, store))

    class FakeBridge:
        def patch_manager(self) -> PatchManager:
            return manager

    monkeypatch.setattr(re_tools, "bridge", FakeBridge())
    out = re_tools.patch_set([{"addr": 0x02000000, "bytes": "deadbeef"}])
    assert out["ok"] is True and out["writes"] == 1
    listed = re_tools.patch_list()
    assert listed["active"] is True and listed["writes"][0]["bytes"] == "deadbeef"
    assert re_tools.patch_apply() == {"ok": True, "writes": 1}
    assert re_tools.patch_clear()["cleared"] == 1
    assert re_tools.patch_list()["active"] is False


def test_savestate_load_reapplies_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    """`savestate_load` reapplies the active patch after a successful load."""
    debugger = FakeDebugger()
    manager = PatchManager(cast(Debugger, debugger), cast(FileStore, FakeStore()))
    manager.set([{"addr": 0x02000000, "bytes": "aa"}], persist=False)

    class FakeBridge:
        def patch_manager(self) -> PatchManager:
            return manager

    monkeypatch.setattr(control_tools, "bridge", FakeBridge())
    monkeypatch.setattr(
        control_tools,
        "control_call",
        lambda *a, **k: {"ok": True, "path": "/tmp/state.sav"},
    )
    out = control_tools.savestate_load(1)
    assert out["patch_reapplied"] == 1
    assert debugger.writes[-1] == (0x02000000, b"\xaa")


def test_patch_json_roundtrip() -> None:
    patch = Patch.from_specs([{"addr": 0x02000000, "bytes": "0102"}])
    assert Patch.from_json(patch.to_json()).to_specs() == patch.to_specs()
    assert Patch.from_json('{"writes": []}').writes == ()
