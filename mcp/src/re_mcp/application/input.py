"""Application service: input macros (tap/sequence) over the control channel."""
import time
from collections.abc import Callable

from ..domain.input import MAX_TOTAL_MS, NO_KEY, InputStep, touch_point
from .ports import ControlChannel


class InputMacros:
    """Service: input macros (tap and sequence, for keys or the touch screen)."""

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
        self._press_release("input.key", {"mask": mask}, ms)

    def touch_tap(self, x: int, y: int, ms: int) -> None:
        """Touch ``(x, y)``, wait ``ms`` and release (always releases, even on error).

        Raises:
            ValueError: If the point is outside the touch screen.
        """
        px, py = touch_point(x, y)
        self._press_release("input.touch", {"x": px, "y": py}, ms)

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
                if step.touch is not None:
                    x, y = step.touch
                    self._press_release("input.touch", {"x": x, "y": y}, step.ms)
                elif step.mask is not None and step.mask != NO_KEY:
                    self._press_release("input.key", {"mask": step.mask}, step.ms)
                if step.after_ms:
                    self._sleep(step.after_ms / 1000.0)
        finally:
            self._channel.call("input.release")

    def _press_release(self, method: str, params: dict, ms: int) -> None:
        """Press via ``method``, hold for ``ms`` and release (release on error too)."""
        self._channel.call(method, params)
        try:
            self._sleep(ms / 1000.0)
        finally:
            self._channel.call("input.release")
