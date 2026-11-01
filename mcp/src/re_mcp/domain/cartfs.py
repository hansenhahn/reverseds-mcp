"""Cartridge filesystem (NitroFS): entities and aggregate, without I/O.

Parses the ROM header and the FNT/FAT tables (format per `ndstool`,
`ndsextract.cpp`). Reading the ROM file is the adapter's responsibility
(`infra/ndsrom.py`); here there is only structure and behavior.
"""
import struct
from dataclasses import dataclass

_MIN_HEADER_SIZE = 0x60
_HEADER_SIZE = 0x200


def _u8(data: bytes, offset: int) -> int:
    return data[offset]


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


@dataclass(frozen=True, slots=True)
class NdsHeader:
    """NDS ROM header (full 0x200 bytes, per GBATEK "DS Cartridge Header")."""

    title: str
    gamecode: str
    makercode: str
    unitcode: int
    encryption_seed: int
    device_capacity: int
    region: int
    rom_version: int
    autostart: int
    arm9_rom_offset: int
    arm9_entry: int
    arm9_ram_address: int
    arm9_size: int
    arm7_rom_offset: int
    arm7_entry: int
    arm7_ram_address: int
    arm7_size: int
    fnt_offset: int
    fnt_size: int
    fat_offset: int
    fat_size: int
    arm9_overlay_offset: int
    arm9_overlay_size: int
    arm7_overlay_offset: int
    arm7_overlay_size: int
    icon_offset: int
    secure_area_crc: int
    secure_area_delay: int
    total_used_size: int
    header_size: int
    logo_crc: int
    header_crc: int

    @classmethod
    def from_bytes(cls, data: bytes) -> "NdsHeader":
        """Parse the full header from the first bytes of the ROM.

        Parameters:
            data (bytes): The first bytes of the ROM (at least 0x60; the full
                header is 0x200, missing bytes are treated as zero).

        Returns:
            NdsHeader: The parsed header.

        Raises:
            ValueError: If `data` is shorter than the minimum header.
        """
        if len(data) < _MIN_HEADER_SIZE:
            raise ValueError("header da ROM truncado")
        if len(data) < _HEADER_SIZE:
            data = data + b"\x00" * (_HEADER_SIZE - len(data))
        title = data[0x00:0x0C].split(b"\x00", 1)[0].decode("ascii", "replace")
        return cls(
            title=title,
            gamecode=data[0x0C:0x10].decode("ascii", "replace"),
            makercode=data[0x10:0x12].decode("ascii", "replace"),
            unitcode=_u8(data, 0x12),
            encryption_seed=_u8(data, 0x13),
            device_capacity=_u8(data, 0x14),
            region=_u8(data, 0x1D),
            rom_version=_u8(data, 0x1E),
            autostart=_u8(data, 0x1F),
            arm9_rom_offset=_u32(data, 0x20),
            arm9_entry=_u32(data, 0x24),
            arm9_ram_address=_u32(data, 0x28),
            arm9_size=_u32(data, 0x2C),
            arm7_rom_offset=_u32(data, 0x30),
            arm7_entry=_u32(data, 0x34),
            arm7_ram_address=_u32(data, 0x38),
            arm7_size=_u32(data, 0x3C),
            fnt_offset=_u32(data, 0x40),
            fnt_size=_u32(data, 0x44),
            fat_offset=_u32(data, 0x48),
            fat_size=_u32(data, 0x4C),
            arm9_overlay_offset=_u32(data, 0x50),
            arm9_overlay_size=_u32(data, 0x54),
            arm7_overlay_offset=_u32(data, 0x58),
            arm7_overlay_size=_u32(data, 0x5C),
            icon_offset=_u32(data, 0x68),
            secure_area_crc=_u16(data, 0x6C),
            secure_area_delay=_u16(data, 0x6E),
            total_used_size=_u32(data, 0x80),
            header_size=_u32(data, 0x84),
            logo_crc=_u16(data, 0x15C),
            header_crc=_u16(data, 0x15E),
        )


@dataclass(frozen=True, slots=True)
class RomInfo:
    """Identity of the ROM currently loaded in the emulator."""

    loaded: bool
    name: str
    path: str
    size: int
    gamecode: str
    checksum: int


@dataclass(frozen=True, slots=True)
class RomDetails:
    """Identity + full header + derived counts of the loaded ROM."""

    info: RomInfo
    header: NdsHeader
    file_count: int
    arm9_overlays: int
    arm7_overlays: int


@dataclass(frozen=True, slots=True)
class FatEntry:
    """A file's ``[start, end)`` range in the ROM."""

    start: int
    end: int

    @property
    def size(self) -> int:
        """The file size, in bytes."""
        return self.end - self.start

    def contains(self, offset: int) -> bool:
        """Whether ``offset`` falls inside the range.

        Parameters:
            offset (int): Offset in the ROM.

        Returns:
            bool: True if ``start <= offset < end``.
        """
        return self.start <= offset < self.end


@dataclass(frozen=True, slots=True)
class FileEntry:
    """A filesystem file: its id in the FAT and its path inside the ROM."""

    file_id: int
    path: str


@dataclass(frozen=True, slots=True)
class Fat:
    """The FAT: one range per file id."""

    entries: tuple[FatEntry, ...]

    @classmethod
    def from_bytes(cls, data: bytes) -> "Fat":
        """Parse the FAT.

        Parameters:
            data (bytes): The FAT contents.

        Returns:
            Fat: The ranges, indexed by file id.
        """
        return cls(
            entries=tuple(
                FatEntry(_u32(data, off), _u32(data, off + 4))
                for off in range(0, len(data) - 7, 8)
            )
        )

    def span(self, file_id: int) -> FatEntry:
        """The range of a file, by id.

        Parameters:
            file_id (int): The id in the FAT.

        Returns:
            FatEntry: The file's range.

        Raises:
            KeyError: If the id does not exist in the FAT.
        """
        if file_id >= len(self.entries):
            raise KeyError(file_id)
        return self.entries[file_id]


@dataclass(frozen=True, slots=True)
class Fnt:
    """The FNT: the filesystem files (path + FAT id)."""

    files: tuple[FileEntry, ...]

    @classmethod
    def from_bytes(cls, data: bytes) -> "Fnt":
        """Parse the FNT, walking the directory tree.

        Parameters:
            data (bytes): The FNT contents.

        Returns:
            Fnt: The files, with their id (in the FAT) and path.
        """
        out: list[FileEntry] = []

        def walk(dir_id: int, prefix: str) -> None:
            base = 8 * (dir_id & 0xFFF)
            pos = _u32(data, base)
            file_id = _u16(data, base + 4)
            while True:
                type_len = data[pos]
                pos += 1
                name_len = type_len & 0x7F
                if name_len == 0:
                    break
                name = data[pos : pos + name_len].decode("ascii", "replace")
                pos += name_len
                if type_len & 0x80:
                    sub_id = _u16(data, pos)
                    pos += 2
                    walk(sub_id, prefix + name + "/")
                else:
                    out.append(FileEntry(file_id=file_id, path=prefix + name))
                    file_id += 1

        walk(0, "/")
        return cls(files=tuple(out))


class NdsFs:
    """Aggregate: the ROM filesystem (FNT + FAT), with lookup by path/offset."""

    def __init__(self, fnt: Fnt, fat: Fat) -> None:
        self._fnt = fnt
        self._fat = fat
        self._by_path = {entry.path: entry for entry in fnt.files}

    @classmethod
    def from_bytes(cls, fnt: bytes, fat: bytes) -> "NdsFs":
        """Build the filesystem from the FNT and FAT tables.

        Parameters:
            fnt (bytes): The FNT contents.
            fat (bytes): The FAT contents.

        Returns:
            NdsFs: The filesystem.
        """
        return cls(Fnt.from_bytes(fnt), Fat.from_bytes(fat))

    def file_count(self) -> int:
        """The number of files."""
        return len(self._fnt.files)

    def files(self) -> list[FileEntry]:
        """The files (id and path)."""
        return list(self._fnt.files)

    def span(self, path: str) -> FatEntry | None:
        """The range of a file by path, or None if it does not exist.

        Parameters:
            path (str): The file path inside the ROM.

        Returns:
            FatEntry | None: The range, or None.
        """
        entry = self._by_path.get(path)
        return self._fat.span(entry.file_id) if entry is not None else None

    def file_for_offset(self, offset: int) -> str | None:
        """The path of the file containing ``offset``, or None.

        Parameters:
            offset (int): Offset in the ROM.

        Returns:
            str | None: The path, or None.
        """
        for entry in self._fnt.files:
            if self._fat.span(entry.file_id).contains(offset):
                return entry.path
        return None
