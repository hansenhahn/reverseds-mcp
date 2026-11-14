"""CPU RAM write trace service and tools (no emulator)."""
import pytest

from re_mcp.application.ram_trace import RamTrace
from re_mcp.domain.ram_trace import RamWrite
from re_mcp.tools import ram_trace as tools


class FakeClock:
    """Deterministic clock: advances on each call."""

    def __init__(self, step: float = 0.25) -> None:
        self.now = 0.0
        self.step = step

    def __call__(self) -> float:
        value = self.now
        self.now += self.step
        return value


class FakeChannel:
    """Channel serving queued ``event.ram`` messages and recording calls."""

    def __init__(self, messages: list[dict] | None = None) -> None:
        self.messages = list(messages or [])
        self.calls: list[tuple[str, dict | None]] = []

    def call(
        self, method: str, params: dict | None = None, timeout: float | None = None
    ) -> dict:
        self.calls.append((method, params))
        return {"ok": True}

    def read_message(self, timeout: float) -> dict | None:
        return self.messages.pop(0) if self.messages else None

    def close(self) -> None:
        pass


def _write(cpu: int, addr: int, val: int, width: int, pc: int) -> dict:
    return {"cpu": cpu, "addr": addr, "val": val, "width": width, "pc": pc}


def test_start_sends_range_and_batch() -> None:
    channel = FakeChannel()
    RamTrace(channel).start(0x02200000, 0x02300000, batch=64, timeout_ms=50, max_items=128)
    method, params = channel.calls[0]
    assert method == "ram.write_trace.start"
    assert params == {
        "start": 0x02200000,
        "end": 0x02300000,
        "batch": 64,
        "timeout_ms": 50,
        "max_items": 128,
    }


def test_collect_filters_by_cpu_pc_and_range() -> None:
    message = {
        "method": "event.ram",
        "params": {
            "writes": [
                _write(0, 0x02200010, 0xAB, 4, 0x02001000),
                _write(1, 0x02200020, 0xCD, 2, 0x02002000),
                _write(0, 0x02200030, 0xEF, 1, 0x02001000),
            ],
            "count": 3,
            "dropped": 0,
        },
    }
    channel = FakeChannel([message])
    writes = RamTrace(channel, clock=FakeClock()).collect(
        1.0, addr_start=0x02200000, addr_end=0x02200025, cpu=0, pc=0x02001000
    )
    assert writes == [RamWrite(0, 0x02200010, 0xAB, 4, 0x02001000)]


def test_collect_respects_max_items() -> None:
    message = {
        "method": "event.ram",
        "params": {
            "writes": [_write(0, 0x02200000 + i, i, 1, 0x02000000) for i in range(10)],
            "count": 10,
            "dropped": 0,
        },
    }
    channel = FakeChannel([message])
    writes = RamTrace(channel, clock=FakeClock()).collect(1.0, max_items=3)
    assert len(writes) == 3


def test_summarize_groups_by_addr_width_pc() -> None:
    writes = [
        RamWrite(0, 0x02200000, 1, 4, 0x02001000),
        RamWrite(0, 0x02200000, 2, 4, 0x02001000),
        RamWrite(0, 0x02200004, 3, 5, 0x02001000),
    ]
    groups = RamTrace.summarize(writes)
    assert [(g.addr, g.width, g.count) for g in groups] == [
        (0x02200000, 4, 2),
        (0x02200004, 5, 1),
    ]


class FakeBridge:
    """Bridge stub returning a control channel."""

    def __init__(self, channel: FakeChannel) -> None:
        self._channel = channel

    def control(self) -> FakeChannel:
        return self._channel


def test_watch_range_starts_collects_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = {
        "method": "event.ram",
        "params": {
            "writes": [_write(0, 0x02200000, 0x1234, 4, 0x02003c50)],
            "count": 1,
            "dropped": 0,
        },
    }
    channel = FakeChannel([message])
    monkeypatch.setattr(tools, "bridge", FakeBridge(channel))
    # watch_range uses time.monotonic; patch it to a deterministic clock.
    real_trace = RamTrace
    monkeypatch.setattr(
        tools, "RamTrace", lambda ch: real_trace(ch, clock=FakeClock())
    )
    out = tools.watch_range(0x02200000, 0x02300000, seconds=1.0)
    assert out["count"] == 1
    assert out["writes"][0] == {
        "cpu": "arm9",
        "addr": "0x02200000",
        "value": "0x00001234",
        "width": 4,
        "pc": "0x02003c50",
    }
    assert [call[0] for call in channel.calls] == [
        "ram.write_trace.start",
        "ram.write_trace.stop",
    ]
