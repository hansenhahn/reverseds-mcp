"""Runtime NitroFS override service and tools (no emulator)."""
import pytest

from re_mcp.application.cart_override import CartOverride, CartOverrideError
from re_mcp.domain.cartfs import FatEntry, FileEntry, NdsHeader
from re_mcp.tools import cart_override as tools


class FakeChannel:
    """Control channel recording calls and returning canned results."""

    def __init__(self, results: dict[str, dict] | None = None) -> None:
        self.calls: list[tuple[str, dict | None]] = []
        self.results = results or {}

    def call(
        self, method: str, params: dict | None = None, timeout: float | None = None
    ) -> dict:
        self.calls.append((method, params))
        return self.results.get(method, {"ok": True})

    def read_message(self, timeout: float) -> dict | None:
        return None

    def close(self) -> None:
        pass


class FakeCartFs:
    """CartFs with a fixed path→range table."""

    def __init__(self, spans: dict[str, FatEntry] | None = None) -> None:
        self._spans = spans or {}

    def span(self, path: str) -> FatEntry | None:
        return self._spans.get(path)

    def header(self) -> NdsHeader:
        raise NotImplementedError

    def file_count(self) -> int:
        return len(self._spans)

    def files(self) -> list[FileEntry]:
        return []

    def file_for_offset(self, offset: int) -> str | None:
        return None

    def read_file(self, path: str) -> bytes:
        raise NotImplementedError


WD_TT = FatEntry(0x04E21200, 0x04F8AE00)


def _service(
    spans: dict[str, FatEntry] | None = None, results: dict[str, dict] | None = None
) -> tuple[CartOverride, FakeChannel]:
    channel = FakeChannel(results)
    return CartOverride(channel, FakeCartFs(spans or {"/mi/wd/wd_tt": WD_TT})), channel


def test_set_resolves_and_sends_range() -> None:
    """`set` resolves the path in the FAT and sends its absolute range."""
    service, channel = _service()
    service.set("/mi/wd/wd_tt", "/tmp/wd_tt_patched")
    method, params = channel.calls[0]
    assert method == "cart.override.set"
    assert params == {
        "start": 0x04E21200,
        "end": 0x04F8AE00,
        "host_path": "/tmp/wd_tt_patched",
    }


def test_clear_reload_stats_send_range() -> None:
    """Clear/reload/stats resolve the same path to the same range."""
    service, channel = _service()
    service.clear("/mi/wd/wd_tt")
    service.reload("/mi/wd/wd_tt")
    service.stats("/mi/wd/wd_tt")
    assert [c[0] for c in channel.calls] == [
        "cart.override.clear",
        "cart.override.reload",
        "cart.override.stats",
    ]
    for _, params in channel.calls:
        assert params == {"start": 0x04E21200, "end": 0x04F8AE00}


def test_missing_path_raises_without_calling_emulator() -> None:
    """A path absent from the FNT/FAT fails before touching the channel."""
    service, channel = _service()
    with pytest.raises(CartOverrideError):
        service.set("/nope", "/tmp/x")
    assert channel.calls == []


class FakeBridge:
    """Bridge stub exposing refresh_rom and the override service."""

    def __init__(self, service: CartOverride) -> None:
        self._service = service

    def refresh_rom(self) -> None:
        pass

    def cart_override(self) -> CartOverride:
        return self._service


def test_tool_set_returns_rom_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool exposes rom_start/rom_end/host_size from the channel result."""
    service, _ = _service(
        results={"cart.override.set": {"ok": True, "start": 0x04E21200,
                                       "end": 0x04F8AE00, "host_size": 1481728}}
    )
    monkeypatch.setattr(tools, "bridge", FakeBridge(service))
    out = tools.cart_override_set("/mi/wd/wd_tt", "/tmp/wd_tt_patched")
    assert out == {
        "path": "/mi/wd/wd_tt",
        "rom_start": 0x04E21200,
        "rom_end": 0x04F8AE00,
        "host_size": 1481728,
    }


def test_tool_set_missing_path_is_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A path absent from the FS becomes an error with a hint."""
    service, _ = _service(spans={})
    monkeypatch.setattr(tools, "bridge", FakeBridge(service))
    out = tools.cart_override_set("/nope", "/tmp/x")
    assert "error" in out and "hint" in out


def test_tool_stats_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stats returns the emulator counters plus the path."""
    service, _ = _service(
        results={"cart.override.stats": {"hits": 12, "bytes": 48, "loaded": True}}
    )
    monkeypatch.setattr(tools, "bridge", FakeBridge(service))
    out = tools.cart_override_stats("/mi/wd/wd_tt")
    assert out == {"path": "/mi/wd/wd_tt", "hits": 12, "bytes": 48, "loaded": True}


def test_tool_list_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """List returns the emulator override metadata unchanged."""
    overrides = [{"start": 1, "end": 4, "host_path": "/tmp/x", "loaded": True}]
    service, _ = _service(results={"cart.override.list": {"overrides": overrides}})
    monkeypatch.setattr(tools, "bridge", FakeBridge(service))
    assert tools.cart_override_list() == {"overrides": overrides}
