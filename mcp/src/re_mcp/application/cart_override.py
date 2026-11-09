"""Application service: runtime content overrides for NitroFS files."""
from .ports import CartFs, ControlChannel


class CartOverrideError(RuntimeError):
    """A path does not exist in the NitroFS or has no FAT range."""


class CartOverride:
    """Resolve NitroFS paths to ROM ranges and manage emulator overrides.

    The mapping ``path -> [start, end)`` comes from the FAT of the loaded ROM;
    the emulator serves the host file bytes for that absolute range on every
    cart data read.
    """

    def __init__(self, channel: ControlChannel, cartfs: CartFs) -> None:
        """Build the service over the control channel and the ROM filesystem.

        Parameters:
            channel (ControlChannel): A connected control channel.
            cartfs (CartFs): The filesystem of the loaded ROM.
        """
        self._channel = channel
        self._cartfs = cartfs

    def _range(self, path: str) -> tuple[int, int]:
        """Resolve a NitroFS path to its absolute ``[start, end)`` ROM range.

        Parameters:
            path (str): The file path inside the ROM.

        Returns:
            tuple[int, int]: The absolute start and end offsets.

        Raises:
            CartOverrideError: If the path is not in the FNT/FAT.
        """
        span = self._cartfs.span(path)
        if span is None:
            raise CartOverrideError(f"arquivo não encontrado no NitroFS: {path}")
        return span.start, span.end

    def set(self, path: str, host_path: str) -> dict:
        """Register an override for ``path`` using the host file.

        Parameters:
            path (str): The file path inside the ROM.
            host_path (str): Path read by the emulator process.

        Returns:
            dict: The control-channel result.
        """
        start, end = self._range(path)
        return self._channel.call(
            "cart.override.set",
            {"start": start, "end": end, "host_path": host_path},
        )

    def clear(self, path: str) -> dict:
        """Remove the override for ``path``.

        Parameters:
            path (str): The file path inside the ROM.

        Returns:
            dict: The control-channel result.
        """
        start, end = self._range(path)
        return self._channel.call(
            "cart.override.clear", {"start": start, "end": end}
        )

    def reload(self, path: str) -> dict:
        """Reread the host file and publish the new content.

        Parameters:
            path (str): The file path inside the ROM.

        Returns:
            dict: The control-channel result.
        """
        start, end = self._range(path)
        return self._channel.call(
            "cart.override.reload", {"start": start, "end": end}
        )

    def stats(self, path: str) -> dict:
        """Return the read counters of the override for ``path``.

        Parameters:
            path (str): The file path inside the ROM.

        Returns:
            dict: The control-channel result.
        """
        start, end = self._range(path)
        return self._channel.call(
            "cart.override.stats", {"start": start, "end": end}
        )

    def list(self) -> dict:
        """List the overrides registered in the emulator.

        Returns:
            dict: The control-channel result.
        """
        return self._channel.call("cart.override.list")
