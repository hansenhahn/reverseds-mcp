"""Application service: DMA transfer trace over the control channel."""
import time
from collections.abc import Callable

from ..domain.io import DmaTransfer
from .ports import ControlChannel


class DmaTrace:
    """Service: DMA transfer trace, decoding each raw item into a ``DmaTransfer``."""

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
        """Start the DMA trace.

        Returns:
            dict: The control channel result.
        """
        return self._channel.call(
            "dma.trace.start", {"batch": batch, "timeout_ms": timeout_ms}
        )

    def stop(self) -> dict:
        """Stop the DMA trace.

        Returns:
            dict: The control channel result.
        """
        return self._channel.call("dma.trace.stop")

    def collect(self, seconds: float) -> list[DmaTransfer]:
        """Collect the transfers received (``event.dma`` batches) for ``seconds``.

        Parameters:
            seconds (float): Collection duration in seconds.

        Returns:
            list[DmaTransfer]: The decoded transfers.
        """
        transfers: list[DmaTransfer] = []
        deadline = self._clock() + seconds
        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                break
            message = self._channel.read_message(timeout=min(0.5, remaining))
            if message is not None and message.get("method") == "event.dma":
                for raw in message["params"]["transfers"]:
                    transfers.append(
                        DmaTransfer.from_raw(
                            raw["ch"], raw["src"], raw["dst"], raw["cnt"], raw["pc"]
                        )
                    )
        return transfers
