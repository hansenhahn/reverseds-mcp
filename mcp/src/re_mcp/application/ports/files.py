"""Port for artifact storage (the output directory)."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileStore(Protocol):
    """Port for writing/reading artifacts in the MCP output directory."""

    def write_bytes(self, name: str, data: bytes) -> str:
        """Write bytes to ``name`` and return the path.

        Parameters:
            name (str): Name (may include a subdirectory) relative to the output directory.
            data (bytes): The bytes to write.

        Returns:
            str: The absolute path of the written file.
        """
        ...

    def write_text(self, name: str, text: str) -> str:
        """Write text to ``name`` and return the path.

        Parameters:
            name (str): Name relative to the output directory.
            text (str): The text to write.

        Returns:
            str: The absolute path of the written file.
        """
        ...

    def read_bytes(self, name: str) -> bytes | None:
        """Read the bytes of ``name``, or None if it does not exist.

        Parameters:
            name (str): Name relative to the output directory.

        Returns:
            bytes | None: The bytes, or None.
        """
        ...

    def read_text(self, name: str) -> str | None:
        """Read the text of ``name``, or None if it does not exist.

        Parameters:
            name (str): Name relative to the output directory.

        Returns:
            str | None: The text, or None.
        """
        ...
