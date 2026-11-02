"""`dma_trace_read` filters/summary and validation (no emulator)."""
import pytest

from re_mcp.tools import control as control_tools


class FakeChannel:
    """Replays one ``event.dma`` message."""

    def __init__(self, transfers: list[dict]) -> None:
        self._message = {
            "method": "event.dma",
            "params": {"transfers": transfers, "count": len(transfers)},
        }

    def call(self, method: str, params: dict | None = None, timeout: float | None = None) -> dict:
        return {}

    def read_message(self, timeout: float) -> dict | None:
        message, self._message = self._message, None
        return message

    def close(self) -> None:
        pass


class FakeBridge:
    def __init__(self, transfers: list[dict]) -> None:
        self.channel = FakeChannel(transfers)

    def control(self) -> FakeChannel:
        return self.channel


def _transfer(cpu: int, ch: int, src: int, dst: int, pc: int) -> dict:
    return {"cpu": cpu, "ch": ch, "src": src, "dst": dst,
            "cnt": 0x100 | (1 << 26) | (1 << 31), "pc": pc}


TRANSFERS = [
    _transfer(0, 1, 0x02000000, 0x06000000, 0x0201ABCD),
    _transfer(0, 1, 0x02000000, 0x06000000, 0x0201ABCD),
    _transfer(1, 0, 0x021A3C10, 0x07000400, 0x0201ABCD),
]


def test_dma_trace_read_filters_and_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Filters remove audio and summary groups the duplicate VRAM transfers."""
    monkeypatch.setattr(control_tools, "bridge", FakeBridge(TRANSFERS))
    out = control_tools.dma_trace_read(
        0.05, dst_range=[0x06000000, 0x06001000], cpu="arm9", channel=1, summary=True
    )
    assert out["count"] == 2
    assert len(out["groups"]) == 1
    assert out["groups"][0]["count"] == 2
    assert out["groups"][0]["destination"] == "0x06000000"


def test_dma_trace_read_compat_without_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without filters the tool still returns decoded transfers."""
    monkeypatch.setattr(control_tools, "bridge", FakeBridge(TRANSFERS))
    out = control_tools.dma_trace_read(0.05)
    assert out["count"] == 3
    assert len(out["transfers"]) == 3


@pytest.mark.parametrize(
    "kwargs",
    [
        {"dst_range": [1]},
        {"dst_range": [2, 1]},
        {"cpu": "nope"},
        {"channel": 4},
        {"min_len": -1},
        {"max_items": 0},
    ],
)
def test_dma_trace_read_rejects_bad_filters(
    monkeypatch: pytest.MonkeyPatch, kwargs: dict
) -> None:
    """Invalid filters return error + hint."""
    monkeypatch.setattr(control_tools, "bridge", FakeBridge(TRANSFERS))
    out = control_tools.dma_trace_read(0.05, **kwargs)
    assert "error" in out and "hint" in out
