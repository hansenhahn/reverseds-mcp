"""Testes do filesystem nativo do cartucho (FNT/FAT) — sem a ROM real."""
import struct
from pathlib import Path

from re_mcp.domain.cartfs import Fat, Fnt, NdsHeader
from re_mcp.infra.ndsrom import NdsRom


def _fnt() -> bytes:
    """FNT sintética: `/a.txt` (id 0) e `/sub/b.bin` (id 1)."""
    root = struct.pack("<IHH", 16, 0, 1)
    sub = struct.pack("<IHH", 29, 1, 0)
    root_entries = b"\x05a.txt" + b"\x83sub" + struct.pack("<H", 1) + b"\x00"
    sub_entries = b"\x05b.bin" + b"\x00"
    return root + sub + root_entries + sub_entries


def _fat() -> bytes:
    """FAT sintética: id 0 → [0x100,0x110); id 1 → [0x200,0x208)."""
    return struct.pack("<II", 0x100, 0x110) + struct.pack("<II", 0x200, 0x208)


def _rom(path: Path) -> Path:
    """Monta uma ROM sintética (header + FNT + FAT + dados + overlay)."""
    fnt, fat = _fnt(), _fat()
    fnt_off, fat_off, ovl_off = 0x60, 0x60 + len(fnt), 0x300
    size = max(ovl_off + 32, 0x210)
    rom = bytearray(size)
    rom[0x0C:0x10] = b"TEST"
    for off, val in (
        (0x40, fnt_off), (0x44, len(fnt)), (0x48, fat_off), (0x4C, len(fat)),
        (0x50, ovl_off), (0x54, 32), (0x58, 0), (0x5C, 0),
    ):
        struct.pack_into("<I", rom, off, val)
    rom[fnt_off:fnt_off + len(fnt)] = fnt
    rom[fat_off:fat_off + len(fat)] = fat
    rom[0x100:0x110] = b"A" * 16
    rom[0x200:0x208] = b"B" * 8
    struct.pack_into("<8I", rom, ovl_off, 0, 0x02000000, 0x1000, 0x10, 0, 0, 1, 0)
    path.write_bytes(rom)
    return path


def test_parse_header(tmp_path: Path) -> None:
    """O header expõe offsets de FNT/FAT e overlays."""
    header = NdsHeader.from_bytes(_rom(tmp_path / "header.bin").read_bytes()[:0x60])
    assert header.gamecode == "TEST"
    assert header.fnt_offset == 0x60
    assert header.arm9_overlay_size == 32
    assert header.arm7_overlay_size == 0


def test_fnt_tree() -> None:
    """A FNT vira a lista de arquivos com id e caminho."""
    files = Fnt.from_bytes(_fnt()).files
    assert [(f.file_id, f.path) for f in files] == [(0, "/a.txt"), (1, "/sub/b.bin")]


def test_fat_ranges() -> None:
    """A FAT vira faixas `[start, end)` por id, com `contains`."""
    fat = Fat.from_bytes(_fat())
    assert (fat.span(0).start, fat.span(0).end, fat.span(0).size) == (0x100, 0x110, 16)
    assert fat.entries[1].end == 0x208
    assert fat.entries[0].contains(0x108)
    assert not fat.entries[0].contains(0x110)


def test_ndsrom_list_and_offset(tmp_path: Path) -> None:
    """O adaptador lista arquivos e mapeia offset→arquivo."""
    rom = NdsRom(str(_rom(tmp_path / "list.bin")))
    assert rom.file_count() == 2
    assert [e.path for e in rom.files()] == ["/a.txt", "/sub/b.bin"]
    assert rom.file_for_offset(0x108) == "/a.txt"
    assert rom.file_for_offset(0x200) == "/sub/b.bin"
    assert rom.file_for_offset(0x150) is None


def test_ndsrom_read_file(tmp_path: Path) -> None:
    """O adaptador lê o conteúdo pelo caminho."""
    rom = NdsRom(str(_rom(tmp_path / "read.bin")))
    assert rom.read_file("/a.txt") == b"A" * 16
    assert rom.read_file("/sub/b.bin") == b"B" * 8
