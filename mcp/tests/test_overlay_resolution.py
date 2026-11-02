"""Overlay candidates, selection and details (domain/application/tools)."""
import pytest

from re_mcp.application.overlays import OverlayResolver
from re_mcp.domain.overlays import Overlay, OverlayDetails, OverlayHit, OverlayTable
from re_mcp.domain.symbols import Symbol, SymbolTable
from re_mcp.tools import cart as cart_tools
from re_mcp.tools import re as re_tools

BASE = 0x02082960
O22 = Overlay("arm9", 22, BASE, 0x30500, 0x80, 22, flags=0)
O25 = Overlay("arm9", 25, BASE, 0x32DE0, 0x40, 25, flags=0)


class FakeOverlays:
    """Two overlays sharing the same base (22/25)."""

    def __init__(self) -> None:
        self._table = OverlayTable([O22, O25])

    def overlay_list(self, core: str) -> list[Overlay]:
        return self._table.entries() if core == "arm9" else []

    def overlay_for_address(self, addr: int, core: str = "arm9") -> OverlayHit | None:
        return self._table.for_address(addr) if core == "arm9" else None

    def overlay_candidates(self, addr: int, core: str = "arm9") -> list[OverlayHit]:
        return list(self._table.candidates(addr)) if core == "arm9" else []

    def overlay_details(self, index: int, core: str = "arm9") -> OverlayDetails:
        overlay = self._table.by_index(index)
        if overlay is None or core != "arm9":
            raise ValueError("overlay não encontrado")
        return OverlayDetails(overlay, 0x1000 + index, 0x900, True, 0x900)


class FakeBridge:
    """Bridge with the overlay resolver and the pieces used by `addr_valid`."""

    def __init__(self, table: SymbolTable | None = None) -> None:
        self._resolver = OverlayResolver(FakeOverlays())
        self.table = table or SymbolTable([])

    def refresh_rom(self) -> None:
        return None

    def overlays(self) -> FakeOverlays:
        return FakeOverlays()

    def overlay_resolver(self) -> OverlayResolver:
        return self._resolver

    def active_overlay(self, core: str = "arm9") -> int | None:
        return self._resolver.selection(core)[0]

    def clear_overlay(self, core: str = "arm9") -> None:
        self._resolver.clear(core)

    def symbols(self) -> SymbolTable:
        return self.table


def test_resolver_returns_all_candidates() -> None:
    """Shared bases yield both candidates and no silent selection."""
    out = OverlayResolver(FakeOverlays()).resolve(0x020A11C4)
    assert [hit.overlay.index for hit in out.candidates] == [22, 25]
    assert out.ambiguous is True
    assert out.selected is None


def test_resolver_selects_active_overlay() -> None:
    """An explicit/active overlay becomes the selected hit without hiding others."""
    resolver = OverlayResolver(FakeOverlays())
    resolver.select(25)
    out = resolver.resolve(0x020A11C4)
    assert out.selected is not None and out.selected.overlay.index == 25
    assert len(out.candidates) == 2 and out.ambiguous is True


def test_resolver_code_base_offsets() -> None:
    """A code base yields offset_code/prefix_size."""
    resolver = OverlayResolver(FakeOverlays())
    details = resolver.select(25, code_base=BASE + 0x600)
    assert details is not None
    assert details.prefix_size == 0x600
    out = resolver.resolve(0x020A11C4)
    assert out.code_base == BASE + 0x600
    assert out.selected is not None
    assert out.selected.offset_file == 0x020A11C4 - BASE
    assert out.selected.offset_code == 0x020A11C4 - (BASE + 0x600)


def test_resolver_clear_and_invalid_code_base() -> None:
    """Clearing removes the selection; an out-of-range code base is rejected."""
    resolver = OverlayResolver(FakeOverlays())
    resolver.select(25)
    resolver.clear()
    assert resolver.resolve(0x020A11C4).selected is None
    with pytest.raises(ValueError):
        resolver.select(25, code_base=0x03000000)


def test_overlay_for_address_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool exposes candidates, ambiguity and the active selection."""
    monkeypatch.setattr(cart_tools, "bridge", FakeBridge())
    out = cart_tools.overlay_for_address(0x020A11C4)
    assert out["found"] is True
    assert out["ambiguous"] is True
    assert len(out["overlays"]) == 2
    assert out["overlay"] is None
    assert out["offset_file"] is None

    selected = cart_tools.overlay_select(25, code_base=BASE + 0x600)
    assert selected["overlay"] == 25 and selected["prefix_size"] == 0x600
    out = cart_tools.overlay_for_address(0x020A11C4)
    assert out["overlay"]["index"] == 25
    assert out["offset_file"] == 0x020A11C4 - BASE
    assert out["offset_code"] == 0x020A11C4 - (BASE + 0x600)

    cleared = cart_tools.overlay_select(None)
    assert cleared["overlay"] is None
    out = cart_tools.overlay_for_address(0x020A11C4)
    assert out["overlay"] is None


def test_overlay_details_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """`overlay_details` returns y9/FAT/compression and the code base."""
    monkeypatch.setattr(cart_tools, "bridge", FakeBridge())
    out = cart_tools.overlay_details(25, code_base=BASE + 0x600)
    assert out["index"] == 25
    assert out["file_offset"] == 0x1000 + 25
    assert out["file_size"] == 0x900
    assert out["compressed"] is True
    assert out["code_base"] == BASE + 0x600
    assert out["prefix_size"] == 0x600


def test_addr_valid_reports_ambiguity(monkeypatch: pytest.MonkeyPatch) -> None:
    """`addr_valid` lists candidates and does not pick the first when ambiguous."""
    monkeypatch.setattr(re_tools, "bridge", FakeBridge())
    out = re_tools.addr_valid(0x020A11C4)
    assert out["ambiguous"] is True
    assert out["overlay"] is None
    assert [item["index"] for item in out["overlays"]] == [22, 25]


def test_resolver_code_base_without_candidates_is_empty() -> None:
    """A code base with no candidate address is not an error (nothing to resolve)."""
    out = OverlayResolver(FakeOverlays()).resolve(0x03000000, code_base=BASE + 0x600)
    assert out.candidates == ()
    assert out.selected is None
    assert out.code_base == BASE + 0x600


def test_addr_valid_annotates_each_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each overlay candidate gets its own symbol; active overlay wins on top."""
    bridge = FakeBridge()
    bridge.table.add(Symbol(0x020A11C4, "fn_22", overlay=22))
    bridge.table.add(Symbol(0x020A11C4, "fn_25", overlay=25))
    monkeypatch.setattr(re_tools, "bridge", bridge)

    out = re_tools.addr_valid(0x020A11C4)
    by_index = {item["index"]: item["symbol"] for item in out["overlays"]}
    assert by_index == {22: "fn_22", 25: "fn_25"}
    assert out["symbol"] is None

    bridge.overlay_resolver().select(25)
    out = re_tools.addr_valid(0x020A11C4)
    assert out["symbol"] == "fn_25"
