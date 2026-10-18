"""`GdbBackend.connect` lifecycle tests — no real gdb or emulator."""
import subprocess

import pytest

from re_mcp.infra.gdb import DebugError, GdbBackend


class _FakeStdin:
    """Records the commands written to gdb's stdin."""

    def __init__(self) -> None:
        self.written: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.written.append(data)

    def flush(self) -> None: ...


class _FakeProc:
    """Minimal stand-in for ``subprocess.Popen``."""

    def __init__(self) -> None:
        self.stdin = _FakeStdin()
        self.stdout = object()
        self.returncode: int | None = None
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        self.returncode = 0
        return 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def send_signal(self, sig: int) -> None: ...


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> tuple[GdbBackend, list[_FakeProc]]:
    spawned: list[_FakeProc] = []

    def fake_popen(*args: object, **kwargs: object) -> _FakeProc:
        proc = _FakeProc()
        spawned.append(proc)
        return proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        GdbBackend,
        "_read_until_prompt",
        lambda self, timeout: "Remote debugging using 127.0.0.1:3333\n(gdb) ",
    )
    return GdbBackend("gdb-multiarch", 3333, 3334), spawned


def test_connect_same_core_is_idempotent(
    backend: tuple[GdbBackend, list[_FakeProc]],
) -> None:
    """Connecting twice to the same core spawns a single gdb."""
    be, spawned = backend
    be.connect("arm9")
    be.connect("arm9")
    assert len(spawned) == 1


def test_connect_switching_core_detaches_first(
    backend: tuple[GdbBackend, list[_FakeProc]],
) -> None:
    """Switching cores detaches the previous session before reconnecting."""
    be, spawned = backend
    be.connect("arm9")
    be.connect("arm7")
    assert len(spawned) == 2
    assert any(b"detach" in data for data in spawned[0].stdin.written)


def test_connect_respawns_after_gdb_died(
    backend: tuple[GdbBackend, list[_FakeProc]],
) -> None:
    """A dead gdb process is replaced instead of reusing the stale handle."""
    be, spawned = backend
    be.connect("arm9")
    spawned[0].returncode = 1
    be.connect("arm9")
    assert len(spawned) == 2


def test_connect_rejects_unknown_core(
    backend: tuple[GdbBackend, list[_FakeProc]],
) -> None:
    """An invalid core is rejected before touching gdb."""
    be, _ = backend
    with pytest.raises(DebugError):
        be.connect("arm11")


def test_connect_same_core_stops_a_running_target(
    backend: tuple[GdbBackend, list[_FakeProc]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-connecting while the target runs stops it, without spawning a new gdb."""
    be, spawned = backend
    be.connect("arm9")
    monkeypatch.setattr(GdbBackend, "is_running", lambda self: True)
    interrupted: list[bool] = []
    monkeypatch.setattr(GdbBackend, "interrupt", lambda self: interrupted.append(True))
    be.connect("arm9")
    assert len(spawned) == 1
    assert interrupted == [True]
