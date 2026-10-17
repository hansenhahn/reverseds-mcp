"""Porta do filesystem de cartucho (NitroFS) da ROM."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class CartFs(Protocol):
    """Porta para o filesystem da ROM (NitroFS): mapeia offsets em arquivos."""

    def file_count(self) -> int:
        """O número de arquivos listados.

        Returns:
            int: Quantidade de arquivos.
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
