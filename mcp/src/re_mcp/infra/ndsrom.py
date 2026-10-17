"""Filesystem e overlays nativos de uma ROM de NDS (substitui o `ndstool`).

Abre a ROM, lê o header e as tabelas FNT/FAT/overlay diretamente do arquivo, e
resolve offset→arquivo, conteúdo e endereço de RAM→overlay. Sem ferramenta externa.
"""
from typing import BinaryIO

from ..domain.cartfs import FatEntry, FileEntry, parse_fat, parse_fnt, parse_header
from ..domain.overlays import Overlay, OverlayHit, parse_overlays, resolve_address
from ..domain.ports import CartFs, Overlays

_HEADER_SIZE = 0x60
_CORES = ("arm9", "arm7")


class NdsRomError(RuntimeError):
    """Erro ao abrir ou interpretar a ROM."""


class NdsRom(CartFs, Overlays):
    """Filesystem e overlays de uma ROM de NDS, lidos diretamente do arquivo."""

    def __init__(self, rom_path: str) -> None:
        """Abre a ROM e interpreta header, FAT, FNT e tabelas de overlay.

        Parameters:
            rom_path (str): Caminho da ROM.

        Raises:
            NdsRomError: Se a ROM não puder ser aberta ou interpretada.
        """
        self._path = rom_path
        self._fh: BinaryIO
        try:
            self._fh = open(rom_path, "rb")
        except OSError as exc:
            raise NdsRomError(f"não abriu a ROM {rom_path}: {exc}") from exc

        self._header = parse_header(self._read(0, _HEADER_SIZE))
        self._fat: list[FatEntry] = parse_fat(
            self._read(self._header.fat_offset, self._header.fat_size)
        )
        self._files: list[FileEntry] = parse_fnt(
            self._read(self._header.fnt_offset, self._header.fnt_size)
        )
        self._by_path = {entry.path: entry for entry in self._files}
        self._overlays = {core: self._read_overlays(core) for core in _CORES}

    def _read(self, offset: int, size: int) -> bytes:
        self._fh.seek(offset)
        return self._fh.read(size)

    def _read_overlays(self, core: str) -> list[Overlay]:
        if core == "arm9":
            offset, size = self._header.arm9_overlay_offset, self._header.arm9_overlay_size
        else:
            offset, size = self._header.arm7_overlay_offset, self._header.arm7_overlay_size
        if size == 0:
            return []
        return parse_overlays(self._read(offset, size), core)

    def file_count(self) -> int:
        return len(self._files)

    def files(self) -> list[FileEntry]:
        return list(self._files)

    def file_for_offset(self, offset: int) -> str | None:
        for entry in self._files:
            span = self._fat[entry.file_id]
            if span.start <= offset < span.end:
                return entry.path
        return None

    def read_file(self, path: str) -> bytes:
        entry = self._by_path.get(path)
        if entry is None:
            raise NdsRomError(f"arquivo não encontrado: {path}")
        span = self._fat[entry.file_id]
        return self._read(span.start, span.size)

    def overlay_list(self, core: str) -> list[Overlay]:
        if core not in self._overlays:
            raise NdsRomError(f"core desconhecido: {core!r} (use 'arm9' ou 'arm7')")
        return list(self._overlays[core])

    def overlay_for_address(self, addr: int, core: str = "arm9") -> OverlayHit | None:
        return resolve_address(self._overlays.get(core, []), addr)

    def close(self) -> None:
        """Fecha o arquivo da ROM."""
        self._fh.close()
