"""Cartridge filesystem (NitroFS): entities and aggregate, without I/O.

Parses the ROM header and the FNT/FAT tables (format per `ndstool`,
`ndsextract.cpp`). Reading the ROM file is the adapter's responsibility
(`infra/ndsrom.py`); here there is only structure and behavior.
"""
import struct
from dataclasses import dataclass

_HEADER_SIZE = 0x60


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


@dataclass(frozen=True, slots=True)
class NdsHeader:
    """ROM header: where the FNT/FAT and the overlay tables live."""

    gamecode: str
    fnt_offset: int
    fnt_size: int
    fat_offset: int
    fat_size: int
    arm9_overlay_offset: int
    arm9_overlay_size: int
    arm7_overlay_offset: int
    arm7_overlay_size: int

    @classmethod
    def from_bytes(cls, data: bytes) -> "NdsHeader":
        """Parse the header from the first bytes of the ROM.

        Parameters:
            data (bytes): The first bytes of the ROM (at least 0x60).

        Returns:
            NdsHeader: The parsed header.

        Raises:
            ValueError: If `data` is shorter than the minimum header.
        """
        if len(data) < _HEADER_SIZE:
            raise ValueError("header da ROM truncado")
        return cls(
            gamecode=data[0x0C:0x10].decode("ascii", "replace"),
            fnt_offset=_u32(data, 0x40),
            fnt_size=_u32(data, 0x44),
            fat_offset=_u32(data, 0x48),
            fat_size=_u32(data, 0x4C),
            arm9_overlay_offset=_u32(data, 0x50),
            arm9_overlay_size=_u32(data, 0x54),
            arm7_overlay_offset=_u32(data, 0x58),
            arm7_overlay_size=_u32(data, 0x5C),
        )


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
