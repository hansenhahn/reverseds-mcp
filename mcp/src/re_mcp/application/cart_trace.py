"""Application service: cartridge read trace over the control channel."""
import time
from collections.abc import Callable

from .ports import CartFs, ControlChannel


class TraceError(RuntimeError):
    """Error starting the cartridge trace."""


class CartTrace:
    """Service: cartridge read trace over the control channel."""

    def __init__(
        self, channel: ControlChannel, clock: Callable[[], float] = time.monotonic
    ) -> None:
        """Build the service over a control channel.

        Parameters:
            channel (ControlChannel): A connected control channel.
            clock (Callable[[], float]): Monotonic clock (injectable for tests).
        """
        self._channel = channel
        self._clock = clock

    def start(self, batch: int = 256, timeout_ms: int = 100) -> dict:
        """Start the cartridge read trace.

        Returns:
            dict: The control channel result.
        """
        return self._channel.call(
            "cart.trace.start", {"batch": batch, "timeout_ms": timeout_ms}
        )

    def stop(self) -> dict:
        """Stop the cartridge read trace.

        Returns:
            dict: The control channel result.
        """
        return self._channel.call("cart.trace.stop")

    def collect(self, seconds: float) -> list[dict]:
        """Collect the reads received (``event.cart`` batches) for ``seconds``.

        Parameters:
            seconds (float): Collection duration in seconds.

        Returns:
            list[dict]: The collected reads ``{addr, length, command}``.
        """
        reads: list[dict] = []
        deadline = self._clock() + seconds
        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                break
            message = self._channel.read_message(timeout=min(0.5, remaining))
            if message is not None and message.get("method") == "event.cart":
                reads.extend(message["params"]["reads"])
        return reads

    def by_file(
        self, seconds: float, fs: CartFs, batch: int = 256, timeout_ms: int = 100
    ) -> dict[str, int]:
        """Start the trace, collect for ``seconds`` and aggregate by FS file.

        Parameters:
            seconds (float): Collection duration.
            fs (CartFs): The filesystem used to translate offsets into files.
            batch (int): Items per batch.
            timeout_ms (int): Batch timeout in milliseconds.

        Returns:
            dict[str, int]: Count per path (``<não-arquivo>`` for offsets outside the FS).

        Raises:
            TraceError: If the trace does not start.
        """
        started = self.start(batch, timeout_ms)
        if "error" in started:
            raise TraceError(str(started["error"]))
        try:
            reads = self.collect(seconds)
        finally:
            self.stop()
        files: dict[str, int] = {}
        for read in reads:
            path = fs.file_for_offset(read["addr"]) or "<não-arquivo>"
            files[path] = files.get(path, 0) + 1
        return files
