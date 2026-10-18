"""Pure IO decode tests (schema + VRAM layout) — without the emulator."""
from re_mcp.domain.io import DecodedRegister, DmaTransfer, IoMap, VramLayout

_MAP = IoMap.default()


def _decode(addr: int, raw: int, size: int) -> DecodedRegister:
    decoded = _MAP.decode(addr, raw.to_bytes(size, "little"))
    assert decoded is not None
    return decoded


def _fields(decoded: DecodedRegister) -> dict[str, int]:
    return {f.name: f.value for f in decoded.fields}


def test_dispcnt_a_smoke_value() -> None:
    """DISPCNT A = 0x4001111D decodes to mode 5, BG0 and OBJ on, graphics."""
    decoded = _decode(0x04000000, 0x4001111D, 4)
    fields = _fields(decoded)
    assert decoded.name == "DISPCNT_A"
    assert decoded.raw == 0x4001111D
    assert fields["bg_mode"] == 5
    assert fields["bg0_enable"] == 1
    assert fields["obj_enable"] == 1
    assert fields["display_mode"] == 1


def test_powcnt1_smoke_value() -> None:
    """POWCNT1 = 0x020F enables LCD, both 2D engines and the 3D engine."""
    fields = _fields(_decode(0x04000304, 0x020F, 2))
    assert fields["lcd_enable"] == 1
    assert fields["engine_a_2d"] == 1
    assert fields["engine_b_2d"] == 1
    assert fields["engine_3d_render"] == 1
    assert fields["display_swap"] == 0


def test_disp3dcnt_smoke_value() -> None:
    """DISP3DCNT = 0x19 enables texture mapping, alpha blending and anti-aliasing."""
    fields = _fields(_decode(0x04000060, 0x19, 4))
    assert fields["texture_mapping"] == 1
    assert fields["shading"] == 0
    assert fields["alpha_blending"] == 1
    assert fields["anti_aliasing"] == 1


def test_vramcnt_smoke_values() -> None:
    """VRAMCNT A/B/C and H decode to their enable/MST/offset fields; 0x247 is WRAMCNT."""
    assert _fields(_decode(0x04000240, 0x83, 1)) == {"mst": 3, "offset": 0, "enable": 1}
    assert _fields(_decode(0x04000241, 0x8B, 1)) == {"mst": 3, "offset": 1, "enable": 1}
    assert _fields(_decode(0x04000242, 0x80, 1)) == {"mst": 0, "offset": 0, "enable": 1}
    assert _fields(_decode(0x04000248, 0x03, 1)) == {"mst": 3, "offset": 0, "enable": 0}
    assert _fields(_decode(0x04000247, 0x03, 1)) == {"wram": 3}


def test_descriptions_flow_through() -> None:
    """The register and field descriptions from the schema reach the decode."""
    decoded = _decode(0x04000000, 0x4001111D, 4)
    assert decoded.description == "LCD control (engine A)"
    by_name = {f.name: f for f in decoded.fields}
    assert by_name["obj_1d_mapping"].description == "OBJ tile VRAM mapping (0=2D, 1=1D)"


def test_unknown_address_returns_none() -> None:
    """An address outside the schema is not decodable."""
    assert _MAP.decode(0x0400FFFF, b"\x00\x00\x00\x00") is None
    assert _MAP.register_at(0x0400FFFF) is None


def test_vram_layout_smoke() -> None:
    """The smoke VRAMCNT values resolve to the expected bank→window bindings."""
    banks = {"A": 0x83, "B": 0x8B, "C": 0x80, "D": 0x84, "E": 0x83,
             "F": 0x82, "G": 0x8C, "H": 0x03, "I": 0x00}
    bindings = {b.bank: b for b in VramLayout.from_vramcnt(banks).bindings()}
    assert set(bindings) == {"A", "B", "C", "D", "E", "F", "G"}  # H, I disabled
    assert bindings["C"].target == "lcdc"
    assert bindings["C"].address == 0x6840000
    assert bindings["D"].target == "engine_b_obj"
    assert bindings["D"].address == 0x6600000
    assert bindings["A"].target == "texture_image_slot0"
    assert bindings["F"].target == "engine_a_obj"
    assert bindings["F"].address == 0x6400000
    assert bindings["G"].target == "engine_a_bg_extpal"


def test_dma_transfer_decodes_cnt() -> None:
    """A raw DMA description decodes the DMAxCNT with the schema field names."""
    # word_count=0x100, dest=inc, src=inc, 32-bit, start immediately, enable
    cnt = 0x100 | (1 << 26) | (1 << 31)
    transfer = DmaTransfer.from_raw(0, 0x02000000, 0x06000000, cnt, 0x0201ABCD)
    assert transfer.length == 0x100 * 4
    assert transfer.source.control == "inc"
    assert transfer.destination.control == "inc"
    assert transfer.destination.address == 0x06000000
    assert transfer.pc == 0x0201ABCD
    fields = {f.name: f for f in transfer.control.fields}
    assert fields["transfer_32bit"].value == 1
    assert fields["start_timing"].meaning == "immediately"
    assert fields["enable"].value == 1


def test_dma_transfer_16bit_length() -> None:
    """A 16-bit transfer with dest=dec decodes length and the endpoint control."""
    cnt = 0x10 | (1 << 21) | (1 << 31)  # word_count=0x10, dest=dec, 16-bit, enable
    transfer = DmaTransfer.from_raw(1, 0x02000000, 0x06000000, cnt, 0)
    assert transfer.length == 0x10 * 2
    assert transfer.destination.control == "dec"
