"""Application service: DMA transfer trace over the control channel."""
import time
from collections.abc import Callable
from dataclasses import dataclass

from ..domain.io import DmaTransfer
from .ports import ControlChannel


@dataclass(frozen=True, slots=True)
class DmaGroup:
    """Aggregated DMA transfers with the same origin/destination/metadata."""

    channel: int
    cpu: int
    source: int
    destination: int
    length: int
    pc: int
    count: int


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

    @staticmethod
    def _matches(
        transfer: DmaTransfer,
        dst_range: tuple[int, int] | None,
        src_range: tuple[int, int] | None,
        cpu: int | None,
        channel: int | None,
        min_len: int,
    ) -> bool:
        """Whether ``transfer`` passes the optional filters."""
        if cpu is not None and transfer.cpu != cpu:
            return False
        if channel is not None and transfer.channel != channel:
            return False
        if transfer.length < min_len:
            return False
        if dst_range is not None:
            low, high = dst_range
            if not low <= transfer.destination.address < high:
                return False
        if src_range is not None:
            low, high = src_range
            if not low <= transfer.source.address < high:
                return False
        return True

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

    def collect(
        self,
        seconds: float,
        *,
        dst_range: tuple[int, int] | None = None,
        src_range: tuple[int, int] | None = None,
        cpu: int | None = None,
        channel: int | None = None,
        min_len: int = 0,
        max_items: int | None = None,
    ) -> list[DmaTransfer]:
        """Collect the transfers received (``event.dma`` batches) for ``seconds``.

        Parameters:
            seconds (float): Collection duration in seconds.
            dst_range (tuple[int, int] | None): ``[start, end)`` destination filter.
            src_range (tuple[int, int] | None): ``[start, end)`` source filter.
            cpu (int | None): 0=ARM9, 1=ARM7.
            channel (int | None): DMA channel filter.
            min_len (int): Minimum transfer length in bytes.
            max_items (int | None): Maximum number of transfers to return.

        Returns:
            list[DmaTransfer]: The decoded (and filtered) transfers.
        """
        if max_items is not None and max_items <= 0:
            return []
        transfers: list[DmaTransfer] = []
        deadline = self._clock() + seconds
        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                break
            message = self._channel.read_message(timeout=min(0.5, remaining))
            if message is not None and message.get("method") == "event.dma":
                for raw in message["params"]["transfers"]:
                    transfer = DmaTransfer.from_raw(
                        raw["cpu"], raw["ch"], raw["src"], raw["dst"], raw["cnt"], raw["pc"]
                    )
                    if not self._matches(
                        transfer, dst_range, src_range, cpu, channel, min_len
                    ):
                        continue
                    transfers.append(transfer)
                    if max_items is not None and len(transfers) >= max_items:
                        return transfers
        return transfers

    @staticmethod
    def summarize(transfers: list[DmaTransfer]) -> list[DmaGroup]:
        """Aggregate transfers by ``(src, dst, len, cpu, channel, pc)``.

        Parameters:
            transfers (list[DmaTransfer]): The transfers to aggregate.

        Returns:
            list[DmaGroup]: Groups sorted by descending count.
        """
        groups: dict[tuple[int, int, int, int, int, int], int] = {}
        for transfer in transfers:
            key = (
                transfer.source.address,
                transfer.destination.address,
                transfer.length,
                transfer.cpu,
                transfer.channel,
                transfer.pc,
            )
            groups[key] = groups.get(key, 0) + 1
        result = [
            DmaGroup(
                source=source,
                destination=destination,
                length=length,
                cpu=cpu,
                channel=channel,
                pc=pc,
                count=count,
            )
            for (source, destination, length, cpu, channel, pc), count in groups.items()
        ]
        result.sort(key=lambda group: (-group.count, group.destination, group.source))
        return result
