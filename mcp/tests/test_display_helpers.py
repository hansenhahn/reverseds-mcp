"""2.3 display↔RAM helpers: pure decoding and tool serialization."""
import struct
from typing import cast

import pytest

from re_mcp.application.display import DisplayReader
from re_mcp.application.ports import Debugger
from re_mcp.domain.display import BgLayer, ObjTileMapping
from re_mcp.domain.io import IoMap, DmaTransfer
from re_mcp.tools import re as re_tools


def test_bg_kind_modes() -> None:
    """BG kinds follow the NDS BG modes."""
    assert BgLayer.from_registers("A", 0, 0, 0).kind == "text"
    assert BgLayer.from_registers("A", 2, 1, 0).kind == "affine"
    assert BgLayer.from_registers("A", 3, 3, 0).kind == "extended"
    assert BgLayer.from_registers("A", 0, 6, 0).kind == "3d"
    assert BgLayer.from_registers("B", 0, 6, 0).kind == "invalid"


def test_text_cell_and_decode() -> None:
    """Text cells resolve the 16-bit entry and tile address."""
    layer = BgLayer.from_registers("B", 0, 0, 0)
    info = layer.cell(0, 0)
    assert info.entry_addr == 0x06200000
    assert (info.char_base, info.bpp) == (0x06200000, 4)
    cell = layer.decode(info, 0x1223)
    assert (cell.tile_index, cell.palette, cell.flip_h, cell.flip_v) == (0x223, 1, False, False)
    assert cell.tile_addr == 0x06200000 + 0x223 * 32


def test_text_512x256_second_block() -> None:
    """512x256 maps place x>=256 in the next 256x256 block."""
    info = BgLayer.from_registers("B", 0, 0, (1 << 14)).cell(256, 0)
    assert info.entry_addr == 0x06200000 + 1024 * 2


def test_affine_cell() -> None:
    """Affine BG uses 8-bit map entries and 256-color tiles."""
    layer = BgLayer.from_registers("A", 2, 2, (1 << 14))
    info = layer.cell(8, 8)
    assert info.kind == "affine"
    assert info.bpp == 8
    assert info.entry_addr == 0x06000000 + 33
    cell = layer.decode(info, 0x42)
    assert cell.tile_addr == 0x06000000 + 0x42 * 64


def test_obj_tile_address_modes() -> None:
    """OBJ 1D/2D mapping uses the raw DISPCNT bits."""
    assert ObjTileMapping.from_registers("A", 1 << 4).address(3, 4) == 0x06400000 + 3 * 32
    assert ObjTileMapping.from_registers("B", 0).address(0x21, 4) == 0x06600000 + 32 + 0x400


class FakeDebugger:
    """Debugger with a sparse memory map."""

    def __init__(self, memory: dict[int, bytes]) -> None:
        self.memory = memory

    def read_memory(self, addr: int, size: int) -> bytes:
        data = self.memory.get(addr)
        if data is not None:
            return data[:size]
        return b"\x00" * size


def _memory() -> dict[int, bytes]:
    tile = bytes(range(32))
    ram = bytearray(0x400000)
    ram[0x100:0x120] = tile
    return {
        0x04001000: (0).to_bytes(4, "little"),
        0x04001008: (0).to_bytes(2, "little"),
        0x0400100A: b"\x00\x00",
        0x0400100C: b"\x00\x00",
        0x0400100E: b"\x00\x00",
        0x0400106C: b"\x00\x00",
        0x04000304: (0x020F).to_bytes(2, "little"),
        0x06200000: (0x1223).to_bytes(2, "little"),
        0x06204460: tile,
        0x02000000: bytes(ram),
    }


def test_display_reader_and_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """The service resolves cells/tiles and finds the tile in RAM."""
    debugger = FakeDebugger(_memory())
    reader = DisplayReader(cast(Debugger, debugger), IoMap.default())
    cell = reader.map_cell("B", 0, 0, 0)
    assert (cell.tile_index, cell.tile_addr) == (0x223, 0x06204460)
    addr, bpp, data = reader.tile_bytes("B", 0x223)
    assert (addr, bpp) == (0x06204460, 4)
    assert data == bytes(range(32))

    tile_addr, depth, addresses = reader.find_tile_in_ram("B", 0x223)
    assert (tile_addr, depth, addresses) == (0x06204460, 4, [0x02000100])

    class FakeBridge:
        def debugger(self) -> FakeDebugger:
            return debugger

        def io_map(self) -> IoMap:
            return IoMap.default()

    monkeypatch.setattr(re_tools, "bridge", FakeBridge())
    out = re_tools.map_cell("B", 0, 0, 0)
    assert out["tile_index"] == 0x223
    assert out["tile_addr"] == "0x06204460"
    out = re_tools.find_tile_in_ram("B", 0x223)
    assert out["addresses"] == ["0x02000100"]


def test_dma_source_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """dma_source serializes the transfers found by the service."""
    transfer = DmaTransfer.from_raw(0, 0, 0x02255720, 0x06207000, 0x84000010, 0x01FF860C)

    class FakeTrace:
        def __init__(self, channel: object) -> None: ...

        def find_destination(
            self, addr: int, seconds: float, batch: int = 256, timeout_ms: int = 100
        ) -> list[DmaTransfer]:
            return [transfer]

    class FakeBridge:
        def control(self) -> object:
            return object()

        def symbols(self) -> object:
            class Table:
                def resolve(self, addr: int) -> None:
                    return None
            return Table()

    monkeypatch.setattr(re_tools, "DmaTrace", FakeTrace)
    monkeypatch.setattr(re_tools, "bridge", FakeBridge())
    out = re_tools.dma_source(0x06207000)
    assert out["count"] == 1
    assert out["hits"][0]["cpu"] == "arm9"
    assert out["hits"][0]["pc"] == "0x01ff860c"
