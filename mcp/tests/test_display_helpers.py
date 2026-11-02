"""2.3 display↔RAM helpers: pure decoding and tool serialization."""
import json
import struct
from typing import cast

import pytest

from re_mcp.application.display import DisplayReader
from re_mcp.application.video import VideoReader
from re_mcp.application.ports import Debugger
from re_mcp.domain.display import BgLayer, ObjTileMapping, rgb555, tile_indices
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
                def resolve(self, addr: int, overlay: int | None = None) -> None:
                    return None
            return Table()

        def active_overlay(self, core: str = "arm9") -> int | None:
            return None

    monkeypatch.setattr(re_tools, "DmaTrace", FakeTrace)
    monkeypatch.setattr(re_tools, "bridge", FakeBridge())
    out = re_tools.dma_source(0x06207000)
    assert out["count"] == 1
    assert out["hits"][0]["cpu"] == "arm9"
    assert out["hits"][0]["pc"] == "0x01ff860c"


def test_cell_from_screen_scroll_and_wrap() -> None:
    """Screen→map applies scroll and wraps inside the map size."""
    layer = BgLayer.from_registers("B", 0, 0, 0, hofs=0x10, vofs=0x20)
    screen = layer.cell_from_screen(0, 0)
    assert (screen.map_x, screen.map_y) == (0x10, 0x20)
    assert screen.screen_rect == (0, 0, 8, 8)
    assert screen.info.entry_addr == 0x06200000 + (0x20 // 8 * 32 + 0x10 // 8) * 2

    wrapped = BgLayer.from_registers("B", 0, 0, 0, hofs=0xF8, vofs=0xF0)
    screen = wrapped.cell_from_screen(16, 16)
    assert (screen.map_x, screen.map_y) == (8, 0)


def test_cell_from_screen_rejects_non_text() -> None:
    """Affine BGs are not supported by the screen→cell MVP."""
    layer = BgLayer.from_registers("A", 2, 2, 0)
    with pytest.raises(ValueError):
        layer.cell_from_screen(0, 0)


def test_display_reader_cell_at_screen() -> None:
    """The reader resolves the map entry for a screen pixel."""
    debugger = FakeDebugger(_memory())
    reader = DisplayReader(cast(Debugger, debugger), IoMap.default())
    screen, cell = reader.cell_at_screen("B", 0, 0, 0)
    assert (screen.map_x, screen.map_y) == (0, 0)
    assert (cell.tile_index, cell.tile_addr) == (0x223, 0x06204460)


def test_cell_at_screen_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """`cell_at_screen` serializes the cell, screen rect and scroll."""
    debugger = FakeDebugger(_memory())

    class FakeBridge:
        def debugger(self) -> FakeDebugger:
            return debugger

        def io_map(self) -> IoMap:
            return IoMap.default()

    monkeypatch.setattr(re_tools, "bridge", FakeBridge())
    out = re_tools.cell_at_screen("B", 0, 0, 0)
    assert out["tile_index"] == 0x223
    assert out["map"] == [0, 0]
    assert out["screen_rect"] == [0, 0, 8, 8]
    assert out["scroll"] == {"hofs": 0, "vofs": 0}


def test_render_layer_highlight(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """`render_layer` draws the 8x8 highlight on the engine's screen PNG."""
    from PIL import Image
    from re_mcp.tools import video as video_tools

    debugger = FakeDebugger(_memory())

    class FakeBridge:
        def debugger(self) -> FakeDebugger:
            return debugger

        def io_map(self) -> IoMap:
            return IoMap.default()

    png = tmp_path / "layer.png"
    Image.new("RGBA", (256, 192), (0, 0, 0, 255)).save(png)

    monkeypatch.setattr(video_tools, "bridge", FakeBridge())
    monkeypatch.setattr(video_tools, "control_call", lambda *a, **k: {})
    monkeypatch.setattr(
        video_tools,
        "save_framebuffer_pngs",
        lambda *a, **k: {"paths": [str(png)]},
    )
    out = video_tools.render_layer(
        "B", "bg0", "top", highlight=[0, 0]
    )
    assert out["screen"] == "top"
    assert out["cell"]["tile_index"] == 0x223
    pixel = Image.open(png).convert("RGBA").getpixel((0, 0))
    assert pixel == (255, 0, 0, 255)


def test_video_state_includes_scroll() -> None:
    """`VideoReader.state` exposes BGxHOFS/VOFS per BG."""
    memory = _memory()
    memory[0x04001010] = (0x10).to_bytes(2, "little")
    memory[0x04001012] = (0x20).to_bytes(2, "little")
    state = VideoReader(cast(Debugger, FakeDebugger(memory)), IoMap.default()).state("B")
    assert len(state.scrolls) == 4
    assert (state.scrolls[0][0].raw, state.scrolls[0][1].raw) == (0x10, 0x20)
    assert (state.scrolls[1][0].raw, state.scrolls[1][1].raw) == (0, 0)


def test_tile_indices_and_rgb555() -> None:
    """Tiles decode to 8x8 indices and BGR555 converts to RGB."""
    tile4 = bytes(range(32))
    rows = tile_indices(tile4, 4)
    assert rows[0][:4] == (0, 0, 1, 0)
    rows8 = tile_indices(bytes(range(64)), 8)
    assert rows8[0][:4] == (0, 1, 2, 3)
    assert rgb555(0x001F) == (255, 0, 0)
    assert BgLayer.from_registers("B", 0, 0, 0).palette_base == 0x05000400


def test_dump_and_render_full_bg_map() -> None:
    """The full map dump and PNG composition use bulk VRAM data."""
    memory = _memory()
    palette = bytearray(512)
    palette[17 * 2:17 * 2 + 2] = (0x001F).to_bytes(2, "little")  # red
    memory[0x05000400] = bytes(palette)
    block = bytearray(0x4480)
    block[0:2] = (0x1223).to_bytes(2, "little")
    block[0x4460:0x4480] = bytes(range(32))
    memory[0x06200000] = bytes(block)
    debugger = FakeDebugger(memory)
    reader = DisplayReader(cast(Debugger, debugger), IoMap.default())

    meta, cells = reader.dump_bg_map("B", 0)
    assert (meta["width"], meta["height"], meta["cell_count"]) == (256, 256, 1024)
    first = cells[0]
    assert (first["tile_index"], first["palette"]) == (0x223, 1)

    png, meta = reader.render_bg_map("B", 0)
    assert meta["cell_count"] == 1024
    from PIL import Image
    from io import BytesIO
    image = Image.open(BytesIO(png)).convert("RGBA")
    assert image.size == (256, 256)
    assert image.getpixel((2, 0)) == (255, 0, 0, 255)
    assert image.getpixel((0, 0)) == (0, 0, 0, 0)


class FakeFiles:
    def __init__(self) -> None:
        self.files: dict[str, str | bytes] = {}

    def write_text(self, name: str, text: str) -> str:
        self.files[name] = text
        return f"/out/{name}"

    def write_bytes(self, name: str, data: bytes) -> str:
        self.files[name] = data
        return f"/out/{name}"


def test_dump_tilemap_and_render_bg_map_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tools write JSON/PNG artifacts and return metadata."""
    memory = _memory()
    debugger = FakeDebugger(memory)
    files = FakeFiles()

    class FakeBridge:
        def debugger(self) -> FakeDebugger:
            return debugger

        def io_map(self) -> IoMap:
            return IoMap.default()

        def files(self) -> FakeFiles:
            return files

    monkeypatch.setattr(re_tools, "bridge", FakeBridge())
    out = re_tools.dump_tilemap("B", 0)
    assert out["cell_count"] == 1024
    payload = json.loads(files.files["bgmap_B_0.json"])
    assert payload["cell_count"] == 1024
    assert len(payload["cells"]) == 1024

    out = re_tools.render_bg_map("B", 0)
    assert out["cell_count"] == 1024
    assert files.files["bgmap_B_0.png"][:8] == b"\x89PNG\r\n\x1a\n"
