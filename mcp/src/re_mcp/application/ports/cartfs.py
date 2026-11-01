"""Port for the cartridge filesystem (NitroFS) of the ROM."""
from typing import Protocol, runtime_checkable

from ...domain.cartfs import FileEntry, NdsHeader


@runtime_checkable
class CartFs(Protocol):
    """Port for the ROM filesystem (NitroFS): lists, maps and reads files."""

    def header(self) -> NdsHeader:
        """Return the full ROM header.

        Returns:
            NdsHeader: The parsed header.

        Raises:
            NdsRomError: If there is no ROM loaded.
        """
        ...

    def file_count(self) -> int:
        """The number of listed files.

        Returns:
            int: Number of files.
        """
        ...

    def files(self) -> list[FileEntry]:
        """List the filesystem files.

        Returns:
            list[FileEntry]: Files with id and path.
        """
        ...

    def file_for_offset(self, offset: int) -> str | None:
        """Return the file containing ``offset`` (or None).

        Parameters:
            offset (int): Offset in the ROM.

        Returns:
            str | None: The file path, or None.
        """
        ...

    def read_file(self, path: str) -> bytes:
        """Read a file's contents by path.

        Parameters:
            path (str): The file path inside the ROM.

        Returns:
            bytes: The file contents.

        Raises:
            NdsRomError: If the file does not exist.
        """
        ...
