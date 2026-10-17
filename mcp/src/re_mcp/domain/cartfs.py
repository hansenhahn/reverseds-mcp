"""Filesystem do cartucho (NitroFS): entidades e agregado, sem I/O.

Interpreta o header da ROM e as tabelas FNT/FAT (formato conforme o `ndstool`,
`ndsextract.cpp`). A leitura do arquivo da ROM é responsabilidade do adaptador
(`infra/ndsrom.py`); aqui só há estrutura e comportamento.
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
    """Header da ROM: onde ficam a FNT/FAT e as tabelas de overlay."""

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
        """Interpreta o header a partir dos primeiros bytes da ROM.

        Parameters:
            data (bytes): Os primeiros bytes da ROM (pelo menos 0x60).

        Returns:
            NdsHeader: O header interpretado.

        Raises:
            ValueError: Se `data` for menor que o header mínimo.
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
    """Faixa ``[start, end)`` de um arquivo na ROM."""

    start: int
    end: int

    @property
    def size(self) -> int:
        """O tamanho do arquivo em bytes."""
        return self.end - self.start

    def contains(self, offset: int) -> bool:
        """Se ``offset`` cai dentro da faixa.

        Parameters:
            offset (int): Offset na ROM.

        Returns:
            bool: True se ``start <= offset < end``.
        """
        return self.start <= offset < self.end


@dataclass(frozen=True, slots=True)
class FileEntry:
    """Um arquivo do filesystem: id na FAT e caminho dentro da ROM."""

    file_id: int
    path: str


@dataclass(frozen=True, slots=True)
class Fat:
    """A FAT: uma faixa por id de arquivo."""

    entries: tuple[FatEntry, ...]

    @classmethod
    def from_bytes(cls, data: bytes) -> "Fat":
        """Interpreta a FAT.

        Parameters:
            data (bytes): Conteúdo da FAT.

        Returns:
            Fat: As faixas, indexadas pelo id do arquivo.
        """
        return cls(
            entries=tuple(
                FatEntry(_u32(data, off), _u32(data, off + 4))
                for off in range(0, len(data) - 7, 8)
            )
        )

    def span(self, file_id: int) -> FatEntry:
        """A faixa de um arquivo pelo id.

        Parameters:
            file_id (int): Id na FAT.

        Returns:
            FatEntry: A faixa do arquivo.

        Raises:
            KeyError: Se o id não existir na FAT.
        """
        if file_id >= len(self.entries):
            raise KeyError(file_id)
        return self.entries[file_id]


@dataclass(frozen=True, slots=True)
class Fnt:
    """A FNT: os arquivos do filesystem (caminho + id na FAT)."""

    files: tuple[FileEntry, ...]

    @classmethod
    def from_bytes(cls, data: bytes) -> "Fnt":
        """Interpreta a FNT, percorrendo a árvore de diretórios.

        Parameters:
            data (bytes): Conteúdo da FNT.

        Returns:
            Fnt: Os arquivos, com id (na FAT) e caminho.
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
    """Agregado: o filesystem da ROM (FNT + FAT), com consulta por caminho/offset."""

    def __init__(self, fnt: Fnt, fat: Fat) -> None:
        self._fnt = fnt
        self._fat = fat
        self._by_path = {entry.path: entry for entry in fnt.files}

    @classmethod
    def from_bytes(cls, fnt: bytes, fat: bytes) -> "NdsFs":
        """Monta o filesystem a partir das tabelas FNT e FAT.

        Parameters:
            fnt (bytes): Conteúdo da FNT.
            fat (bytes): Conteúdo da FAT.

        Returns:
            NdsFs: O filesystem.
        """
        return cls(Fnt.from_bytes(fnt), Fat.from_bytes(fat))

    def file_count(self) -> int:
        """O número de arquivos."""
        return len(self._fnt.files)

    def files(self) -> list[FileEntry]:
        """Os arquivos (id e caminho)."""
        return list(self._fnt.files)

    def span(self, path: str) -> FatEntry | None:
        """A faixa de um arquivo pelo caminho, ou None se não existir.

        Parameters:
            path (str): Caminho do arquivo dentro da ROM.

        Returns:
            FatEntry | None: A faixa, ou None.
        """
        entry = self._by_path.get(path)
        return self._fat.span(entry.file_id) if entry is not None else None

    def file_for_offset(self, offset: int) -> str | None:
        """O caminho do arquivo que contém ``offset``, ou None.

        Parameters:
            offset (int): Offset na ROM.

        Returns:
            str | None: O caminho, ou None.
        """
        for entry in self._fnt.files:
            if self._fat.span(entry.file_id).contains(offset):
                return entry.path
        return None
