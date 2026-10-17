"""Application service: input macros (tap/sequence) over the control channel."""
import time
from collections.abc import Callable

from ..domain.input import MAX_TOTAL_MS, NO_KEY, InputStep
from .ports import ControlChannel


class InputMacros:
    """Service: input macros (tap and sequence) over the control channel."""

    def __init__(
        self, channel: ControlChannel, sleep: Callable[[float], None] = time.sleep
    ) -> None:
        """Build the service over a control channel.

        Parameters:
            channel (ControlChannel): A connected control channel.
            sleep (Callable[[float], None]): Injectable for tests.
        """
        self._channel = channel
        self._sleep = sleep

    def tap(self, mask: int, ms: int) -> None:
        """Press ``mask``, wait ``ms`` and release (always releases, even on error)."""
        self._channel.call("input.key", {"mask": mask})
        try:
            self._sleep(ms / 1000.0)
        finally:
            self._channel.call("input.release")

    def run(self, steps: list[InputStep], max_total_ms: int = MAX_TOTAL_MS) -> None:
        """Run the steps in order; release the input at the end (even on error).

        Raises:
            ValueError: If the total time exceeds ``max_total_ms``.
        """
        total = sum(step.ms + step.after_ms for step in steps)
        if total > max_total_ms:
            raise ValueError(f"sequência longa demais: {total} ms > {max_total_ms} ms")
        try:
            for step in steps:
                if step.mask is not None and step.mask != NO_KEY:
                    self._channel.call("input.key", {"mask": step.mask})
                    self._sleep(step.ms / 1000.0)
                    self._channel.call("input.release")
                if step.after_ms:
                    self._sleep(step.after_ms / 1000.0)
        finally:
            self._channel.call("input.release")
