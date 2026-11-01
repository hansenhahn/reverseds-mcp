"""`rom_details` tool: full header, derived counts and runtime overlay."""
import struct

import pytest

from re_mcp.domain.cartfs import NdsHeader, RomInfo
from re_mcp.domain.overlays import Overlay, OverlayHit
from re_mcp.tools import cart as cart_tools


def _header() -> NdsHeader:
    data = bytearray(0x200)
    data[0x00:0x0C] = b"TEST GAME\0\0\0"
    data[0x0C:0x10] = b"TEST"
    data[0x10:0x12] = b"01"
    data[0x12] = 0x02
    data[0x1D] = 0x80
    data[0x1E] = 0x01
    data[0x1F] = 0x04
    for off, val in (
        (0x20, 0x4000), (0x24, 0x02000800), (0x28, 0x02000000), (0x2C, 0x1000),
        (0x30, 0x8000), (0x34, 0x02380000), (0x38, 0x02380000), (0x3C, 0x800),
        (0x40, 0x10000), (0x44, 0x200), (0x48, 0x10200), (0x4C, 0x40),
        (0x50, 0x10400), (0x54, 0x20), (0x58, 0), (0x5C, 0),
        (0x68, 0x12000), (0x80, 0x100000), (0x84, 0x4000),
    ):
        struct.pack_into("<I", data, off, val)
    struct.pack_into("<H", data, 0x6C, 0x1234)
    struct.pack_into("<H", data, 0x6E, 0x051E)
    struct.pack_into("<H", data, 0x15C, 0xCF56)
    struct.pack_into("<H", data, 0x15E, 0xABCD)
    return NdsHeader.from_bytes(bytes(data))


class FakeCart:
    def header(self) -> NdsHeader:
        return _header()

    def file_count(self) -> int:
        return 1596


OVERLAY = Overlay("arm9", 22, 0x02082960, 0x20000, 0, 22)


class FakeOverlays:
    def overlay_list(self, core: str) -> list[Overlay]:
        return [OVERLAY] if core == "arm9" else []

    def overlay_for_address(self, addr: int, core: str = "arm9") -> OverlayHit | None:
        return OverlayHit(OVERLAY, 0x1E864) if core == "arm9" else None


class FakeDebugger:
    def __init__(self, core: str | None = "arm9") -> None:
        self._core = core

    def core(self) -> str | None:
        return self._core

    def read_register(self, name: str) -> int:
        return 0x020A11C4


class FakeBridge:
    def __init__(self, loaded: bool = True, core: str | None = "arm9") -> None:
        self.loaded = loaded
        self.debugger_instance = FakeDebugger(core)

    def rom_info(self) -> RomInfo:
        if not self.loaded:
            return RomInfo(False, "", "", 0, "", 0)
        return RomInfo(True, "xpa-khe.nds", "/roms/xpa-khe.nds", 0x10000000, "YKGP", 783764040)

    def cartfs(self) -> FakeCart:
        return FakeCart()

    def overlays(self) -> FakeOverlays:
        return FakeOverlays()

    def debugger(self) -> FakeDebugger:
        return self.debugger_instance


def test_rom_details_header_and_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tool returns identity, full header, derived counts and runtime overlay."""
    monkeypatch.setattr(cart_tools, "bridge", FakeBridge())
    out = cart_tools.rom_details()
    assert out["loaded"] is True
    assert out["identity"]["gamecode"] == "YKGP"
    assert out["header"]["title"] == "TEST GAME"
    assert out["header"]["arm9"]["entry"] == 0x02000800
    assert out["header"]["fnt"]["offset"] == 0x10000
    assert out["header"]["header_crc"] == 0xABCD
    assert out["derived"] == {"file_count": 1596, "arm9_overlays": 1, "arm7_overlays": 0}
    assert out["runtime"] == {
        "core": "arm9",
        "pc": "0x020a11c4",
        "overlay": {
            "core": "arm9", "index": 22, "ram_address": 0x02082960,
            "ram_size": 0x20000, "bss_size": 0, "file_id": 22, "offset": 0x1E864,
        },
    }


def test_rom_details_without_debugger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a connected debugger, runtime is null."""
    monkeypatch.setattr(cart_tools, "bridge", FakeBridge(core=None))
    out = cart_tools.rom_details()
    assert out["loaded"] is True
    assert out["runtime"] is None


def test_rom_details_without_rom(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a loaded ROM, the tool says so."""
    monkeypatch.setattr(cart_tools, "bridge", FakeBridge(loaded=False))
    assert cart_tools.rom_details() == {"loaded": False}
