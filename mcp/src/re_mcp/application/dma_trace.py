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

    def find_destination(
        self, addr: int, seconds: float, batch: int = 256, timeout_ms: int = 100
    ) -> list[DmaTransfer]:
        """Collect transfers that wrote the VRAM address ``addr``."""
        self.start(batch, timeout_ms)
        try:
            transfers = self.collect(seconds)
        finally:
            self.stop()
        hits: list[DmaTransfer] = []
        for transfer in transfers:
            unit = 4 if next(
                field for field in transfer.control.fields if field.name == "transfer_32bit"
            ).value else 2
            dst = transfer.destination.address
            control = transfer.destination.control
            if control.startswith("dec"):
                low, high = dst - transfer.length + unit, dst + unit
            elif control.startswith("fixed"):
                low, high = dst, dst + unit
            else:
                low, high = dst, dst + transfer.length
            if low <= addr < high:
                hits.append(transfer)
        return hits

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
                            raw["cpu"], raw["ch"], raw["src"], raw["dst"], raw["cnt"], raw["pc"]
                        )
                    )
        return transfers
