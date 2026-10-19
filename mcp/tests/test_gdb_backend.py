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


def test_backtrace_parses_frames(
    backend: tuple[GdbBackend, list[_FakeProc]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`backtrace` parses gdb's `bt` output, mapping `??` to no function."""
    be, _ = backend
    monkeypatch.setattr(
        be, "_cmd", lambda text, timeout=10: "#0  0x020c3348 in ?? ()\n#1  0x02004800 in main ()\n"
    )
    frames = be.backtrace()
    assert [(f.index, f.pc, f.function) for f in frames] == [
        (0, 0x020C3348, None),
        (1, 0x02004800, "main"),
    ]


def test_breakpoints_parses_and_reads_condition(
    backend: tuple[GdbBackend, list[_FakeProc]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`breakpoints` parses the table and attaches a `stop only if` condition."""
    be, _ = backend
    out = (
        "Num     Type           Disp Enb Address    What\n"
        "1       breakpoint     keep y   0x02000000 \n"
        "2       hw watchpoint  keep y              *(unsigned int*)0x06000000\n"
        "        stop only if r0 == 1\n"
    )
    monkeypatch.setattr(be, "_cmd", lambda text, timeout=10: out)
    bps = be.breakpoints()
    assert (bps[0].number, bps[0].kind, bps[0].address, bps[0].enabled) == (
        1, "breakpoint", 0x02000000, True,
    )
    assert (bps[1].kind, bps[1].address, bps[1].condition) == (
        "watchpoint", 0x06000000, "r0 == 1",
    )


def test_cmd_on_dead_pipe_raises_and_marks_disconnected(
    backend: tuple[GdbBackend, list[_FakeProc]],
) -> None:
    """A broken pipe becomes a DebugError and drops the dead gdb handle."""
    be, spawned = backend
    be.connect("arm9")

    class _BadStdin:
        def write(self, data: bytes) -> int:
            raise BrokenPipeError()

        def flush(self) -> None: ...

    spawned[0].stdin = _BadStdin()  # type: ignore[assignment]
    with pytest.raises(DebugError):
        be._cmd("info registers")
    assert be._proc is None
