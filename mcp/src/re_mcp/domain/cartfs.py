"""Interpretação nativa do filesystem do cartucho NDS (NitroFS).

Lê o header da ROM e parseia as tabelas FNT/FAT (formato conforme o `ndstool`,
`ndsextract.cpp`), sem depender de ferramenta externa. Funções puras: recebem
bytes e devolvem estruturas do domínio.
"""
import struct
from dataclasses import dataclass

_HEADER_SIZE = 0x60


@dataclass(frozen=True, slots=True)
class NdsHeader:
    """Campos do header da ROM usados para localizar FNT/FAT e overlays."""

    gamecode: str
    fnt_offset: int
    fnt_size: int
    fat_offset: int
    fat_size: int
    arm9_overlay_offset: int
    arm9_overlay_size: int
    arm7_overlay_offset: int
    arm7_overlay_size: int


@dataclass(frozen=True, slots=True)
class FileEntry:
    """Um arquivo do filesystem: id na FAT e caminho dentro da ROM."""

    file_id: int
    path: str


@dataclass(frozen=True, slots=True)
class FatEntry:
    """Faixa ``[start, end)`` de um arquivo na ROM."""

    start: int
    end: int

    @property
    def size(self) -> int:
        """O tamanho do arquivo em bytes."""
        return self.end - self.start


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def parse_header(data: bytes) -> NdsHeader:
    """Interpreta o header da ROM (offsets de FNT/FAT e overlays).

    Parameters:
        data (bytes): Os primeiros bytes da ROM (pelo menos 0x60).

    Returns:
        NdsHeader: Os campos relevantes.

    Raises:
        ValueError: Se `data` for menor que o header mínimo.
    """
    if len(data) < _HEADER_SIZE:
        raise ValueError("header da ROM truncado")
    return NdsHeader(
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


def parse_fat(data: bytes) -> list[FatEntry]:
    """Interpreta a FAT: uma faixa ``[start, end)`` por id de arquivo.

    Parameters:
        data (bytes): Conteúdo da FAT.

    Returns:
        list[FatEntry]: As faixas, indexadas pelo id do arquivo.
    """
    return [
        FatEntry(start=_u32(data, off), end=_u32(data, off + 4))
        for off in range(0, len(data) - 7, 8)
    ]


def parse_fnt(data: bytes) -> list[FileEntry]:
    """Interpreta a FNT: percorre a árvore de diretórios e lista os arquivos.

    Parameters:
        data (bytes): Conteúdo da FNT.

    Returns:
        list[FileEntry]: Arquivos com id (na FAT) e caminho (ex.: `/data/x.sdat`).
    """
    files: list[FileEntry] = []

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
                files.append(FileEntry(file_id=file_id, path=prefix + name))
                file_id += 1

    walk(0, "/")
    return files
