"""Filesystem e overlays nativos de uma ROM de NDS (substitui o `ndstool`).

Abre a ROM, lê o header e as tabelas FNT/FAT/overlay diretamente do arquivo, e
delega a interpretação ao domínio (`NdsFs`, `OverlayTable`). Sem ferramenta externa.
"""
from typing import BinaryIO

from ..domain.cartfs import FileEntry, NdsFs, NdsHeader
from ..domain.overlays import Overlay, OverlayHit, OverlayTable
from ..domain.ports import CartFs, Overlays

_HEADER_SIZE = 0x60
_CORES = ("arm9", "arm7")


class NdsRomError(RuntimeError):
    """Erro ao abrir ou interpretar a ROM."""


class NdsRom(CartFs, Overlays):
    """Filesystem e overlays de uma ROM de NDS, lidos diretamente do arquivo."""

    def __init__(self, rom_path: str) -> None:
        """Abre a ROM e interpreta header, FNT/FAT e as tabelas de overlay.

        Parameters:
            rom_path (str): Caminho da ROM.

        Raises:
            NdsRomError: Se a ROM não puder ser aberta.
        """
        self._path = rom_path
        self._fh: BinaryIO
        try:
            self._fh = open(rom_path, "rb")
        except OSError as exc:
            raise NdsRomError(f"não abriu a ROM {rom_path}: {exc}") from exc

        header = NdsHeader.from_bytes(self._read(0, _HEADER_SIZE))
        self._fs = NdsFs.from_bytes(
            self._read(header.fnt_offset, header.fnt_size),
            self._read(header.fat_offset, header.fat_size),
        )
        self._overlays = {core: self._read_overlays(core, header) for core in _CORES}

    def _read(self, offset: int, size: int) -> bytes:
        self._fh.seek(offset)
        return self._fh.read(size)

    def _read_overlays(self, core: str, header: NdsHeader) -> OverlayTable:
        if core == "arm9":
            offset, size = header.arm9_overlay_offset, header.arm9_overlay_size
        else:
            offset, size = header.arm7_overlay_offset, header.arm7_overlay_size
        if size == 0:
            return OverlayTable([])
        return OverlayTable.from_bytes(self._read(offset, size), core)

    def file_count(self) -> int:
        return self._fs.file_count()

    def files(self) -> list[FileEntry]:
        return self._fs.files()

    def file_for_offset(self, offset: int) -> str | None:
        return self._fs.file_for_offset(offset)

    def read_file(self, path: str) -> bytes:
        span = self._fs.span(path)
        if span is None:
            raise NdsRomError(f"arquivo não encontrado: {path}")
        return self._read(span.start, span.size)

    def overlay_list(self, core: str) -> list[Overlay]:
        if core not in self._overlays:
            raise NdsRomError(f"core desconhecido: {core!r} (use 'arm9' ou 'arm7')")
        return self._overlays[core].entries()

    def overlay_for_address(self, addr: int, core: str = "arm9") -> OverlayHit | None:
        table = self._overlays.get(core)
        return table.for_address(addr) if table is not None else None

    def close(self) -> None:
        """Fecha o arquivo da ROM."""
        self._fh.close()
