"""Port for the melonDS control channel (JSON-RPC over a Unix socket)."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class ControlChannel(Protocol):
    """Port for the melonDS control channel (JSON-RPC over a Unix socket)."""

    def call(self, method: str, params: dict | None = None) -> dict:
        """Call a control-channel method and return the ``result``.

        Parameters:
            method (str): Method name (e.g. ``ping``, ``input.key``).
            params (dict | None): Method parameters.

        Returns:
            dict: The JSON-RPC response ``result``.

        Raises:
            ControlError: When the server responds with an error or the connection fails.
        """
        ...

    def read_message(self, timeout: float) -> dict | None:
        """Read the next message (response or notification), or None on timeout.

        Parameters:
            timeout (float): Read timeout in seconds.

        Returns:
            dict | None: The received message, or None.
        """
        ...

    def close(self) -> None:
        """Close the control-channel connection."""
        ...
