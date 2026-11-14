"""Application service: CPU RAM write trace over the control channel."""
import time
from collections.abc import Callable

from ..domain.ram_trace import RamWrite, RamWriteGroup
from .ports import ControlChannel


class RamTrace:
    """Service: CPU data-write trace filtered by an address range."""

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

    def start(
        self,
        addr_start: int,
        addr_end: int,
        batch: int = 256,
        timeout_ms: int = 100,
        max_items: int = 65536,
    ) -> dict:
        """Start the RAM write trace for ``[addr_start, addr_end)``.

        Parameters:
            addr_start (int): First address of the range (inclusive).
            addr_end (int): End address of the range (exclusive).
            batch (int): Writes per batch.
            timeout_ms (int): Batch timeout in milliseconds.
            max_items (int): Ring capacity; the oldest writes are dropped past it.

        Returns:
            dict: The control-channel result.
        """
        return self._channel.call(
            "ram.write_trace.start",
            {
                "start": addr_start,
                "end": addr_end,
                "batch": batch,
                "timeout_ms": timeout_ms,
                "max_items": max_items,
            },
        )

    def stop(self) -> dict:
        """Stop the RAM write trace.

        Returns:
            dict: The control-channel result.
        """
        return self._channel.call("ram.write_trace.stop")

    @staticmethod
    def _matches(
        write: RamWrite,
        addr_start: int | None,
        addr_end: int | None,
        cpu: int | None,
        pc: int | None,
    ) -> bool:
        """Whether ``write`` passes the optional filters."""
        if cpu is not None and write.cpu != cpu:
            return False
        if pc is not None and write.pc != pc:
            return False
        if addr_start is not None and write.addr < addr_start:
            return False
        if addr_end is not None and write.addr >= addr_end:
            return False
        return True

    def collect(
        self,
        seconds: float,
        *,
        addr_start: int | None = None,
        addr_end: int | None = None,
        cpu: int | None = None,
        pc: int | None = None,
        max_items: int | None = None,
    ) -> list[RamWrite]:
        """Collect the writes received (``event.ram`` batches) for ``seconds``.

        Parameters:
            seconds (float): Collection duration in seconds.
            addr_start (int | None): Optional ``[start, end)`` lower bound.
            addr_end (int | None): Optional ``[start, end)`` upper bound.
            cpu (int | None): 0=ARM9, 1=ARM7.
            pc (int | None): Only writes performed at this PC.
            max_items (int | None): Maximum number of writes to return.

        Returns:
            list[RamWrite]: The decoded (and filtered) writes.
        """
        if max_items is not None and max_items <= 0:
            return []
        writes: list[RamWrite] = []
        deadline = self._clock() + seconds
        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                break
            message = self._channel.read_message(timeout=min(0.5, remaining))
            if message is not None and message.get("method") == "event.ram":
                for raw in message["params"]["writes"]:
                    write = RamWrite.from_raw(raw)
                    if not self._matches(write, addr_start, addr_end, cpu, pc):
                        continue
                    writes.append(write)
                    if max_items is not None and len(writes) >= max_items:
                        return writes
        return writes

    @staticmethod
    def summarize(writes: list[RamWrite]) -> list[RamWriteGroup]:
        """Aggregate writes by ``(cpu, addr, width, pc)``.

        Parameters:
            writes (list[RamWrite]): The writes to aggregate.

        Returns:
            list[RamWriteGroup]: Groups sorted by descending count.
        """
        groups: dict[tuple[int, int, int, int], int] = {}
        for write in writes:
            key = (write.cpu, write.addr, write.width, write.pc)
            groups[key] = groups.get(key, 0) + 1
        result = [
            RamWriteGroup(
                cpu=cpu, addr=addr, width=width, pc=pc, count=count
            )
            for (cpu, addr, width, pc), count in groups.items()
        ]
        result.sort(key=lambda group: (-group.count, group.addr, group.pc))
        return result
