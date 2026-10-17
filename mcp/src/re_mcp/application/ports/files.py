"""Porta de armazenamento de artefatos (diretório de saída)."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileStore(Protocol):
    """Porta para gravar/ler artefatos no diretório de saída do MCP."""

    def write_bytes(self, name: str, data: bytes) -> str:
        """Grava bytes em ``name`` e devolve o caminho.

        Parameters:
            name (str): Nome (pode incluir subdiretório) relativo ao diretório de saída.
            data (bytes): Bytes a gravar.

        Returns:
            str: O caminho absoluto do arquivo gravado.
        """
        ...

    def write_text(self, name: str, text: str) -> str:
        """Grava texto em ``name`` e devolve o caminho.

        Parameters:
            name (str): Nome relativo ao diretório de saída.
            text (str): Texto a gravar.

        Returns:
            str: O caminho absoluto do arquivo gravado.
        """
        ...

    def read_bytes(self, name: str) -> bytes | None:
        """Lê os bytes de ``name``, ou None se não existir.

        Parameters:
            name (str): Nome relativo ao diretório de saída.

        Returns:
            bytes | None: Os bytes, ou None.
        """
        ...

    def read_text(self, name: str) -> str | None:
        """Lê o texto de ``name``, ou None se não existir.

        Parameters:
            name (str): Nome relativo ao diretório de saída.

        Returns:
            str | None: O texto, ou None.
        """
        ...
