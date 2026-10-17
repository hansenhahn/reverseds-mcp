"""Porta do filesystem de cartucho (NitroFS) da ROM."""
from typing import Protocol, runtime_checkable

from ...domain.cartfs import FileEntry


@runtime_checkable
class CartFs(Protocol):
    """Porta para o filesystem da ROM (NitroFS): lista, mapeia e lê arquivos."""

    def file_count(self) -> int:
        """O número de arquivos listados.

        Returns:
            int: Quantidade de arquivos.
        """
        ...

    def files(self) -> list[FileEntry]:
        """Lista os arquivos do filesystem.

        Returns:
            list[FileEntry]: Arquivos com id e caminho.
        """
        ...

    def file_for_offset(self, offset: int) -> str | None:
        """Devolve o arquivo que contém ``offset`` (ou None).

        Parameters:
            offset (int): Offset na ROM.

        Returns:
            str | None: O caminho do arquivo, ou None.
        """
        ...

    def read_file(self, path: str) -> bytes:
        """Lê o conteúdo de um arquivo pelo caminho.

        Parameters:
            path (str): Caminho do arquivo dentro da ROM.

        Returns:
            bytes: O conteúdo do arquivo.

        Raises:
            NdsRomError: Se o arquivo não existir.
        """
        ...
