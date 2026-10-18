"""Input model: a sequence step (key or touch) and the mask constants."""
from dataclasses import dataclass

# Sanity cap on the total time of a sequence (avoids an accidental hang).
MAX_TOTAL_MS = 60_000

# Active-low "nothing pressed" mask (the same as the control channel).
NO_KEY = 0xFFF

# Touch screen (bottom screen) bounds, enforced as a domain invariant.
TOUCH_WIDTH = 256
TOUCH_HEIGHT = 192


def touch_point(x: int, y: int) -> tuple[int, int]:
    """Validate and return a touch ``(x, y)`` on the bottom screen.

    Raises:
        ValueError: If the point is outside ``0<=x<TOUCH_WIDTH`` or ``0<=y<TOUCH_HEIGHT``.
    """
    if not (0 <= x < TOUCH_WIDTH and 0 <= y < TOUCH_HEIGHT):
        raise ValueError(
            f"toque fora da tela: ({x}, {y}); esperado "
            f"0<=x<{TOUCH_WIDTH}, 0<=y<{TOUCH_HEIGHT}"
        )
    return (x, y)


@dataclass(frozen=True, slots=True)
class InputStep:
    """An input step: hold an input for ``ms``, then wait ``after_ms``.

    The held input is either a key ``mask`` (active-low buttons) or a ``touch`` at
    ``(x, y)`` on the touch screen; ``mask`` and ``touch`` are mutually exclusive. Both
    None (or ``mask == NO_KEY``) means "just wait".

    Raises:
        ValueError: If both ``mask`` and ``touch`` are set, or the touch is out of bounds.
    """

    ms: int
    after_ms: int = 0
    mask: int | None = None
    touch: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if self.mask is not None and self.touch is not None:
            raise ValueError("passo não pode ter mask e touch ao mesmo tempo")
        if self.touch is not None:
            touch_point(*self.touch)
