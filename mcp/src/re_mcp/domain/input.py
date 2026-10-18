"""Input model: value objects (touch point) and a sequence step."""
from dataclasses import dataclass

# Sanity cap on the total time of a sequence (avoids an accidental hang).
MAX_TOTAL_MS = 60_000

# Active-low "nothing pressed" mask (the same as the control channel).
NO_KEY = 0xFFF

# Touch screen (bottom screen) bounds, enforced by ``TouchPoint``.
TOUCH_WIDTH = 256
TOUCH_HEIGHT = 192


@dataclass(frozen=True, slots=True)
class TouchPoint:
    """A point on the touch screen (bottom screen, engine B).

    Raises:
        ValueError: If the point is outside ``0<=x<TOUCH_WIDTH`` or ``0<=y<TOUCH_HEIGHT``.
    """

    x: int
    y: int

    def __post_init__(self) -> None:
        if not (0 <= self.x < TOUCH_WIDTH and 0 <= self.y < TOUCH_HEIGHT):
            raise ValueError(
                f"toque fora da tela: ({self.x}, {self.y}); esperado "
                f"0<=x<{TOUCH_WIDTH}, 0<=y<{TOUCH_HEIGHT}"
            )


@dataclass(frozen=True, slots=True)
class InputStep:
    """An input step: hold an input for ``ms``, then wait ``after_ms``.

    The held input is either a key ``mask`` (active-low buttons) or a ``touch`` on the
    touch screen; ``mask`` and ``touch`` are mutually exclusive. Both None (or
    ``mask == NO_KEY``) means "just wait".

    Raises:
        ValueError: If both ``mask`` and ``touch`` are set.
    """

    ms: int
    after_ms: int = 0
    mask: int | None = None
    touch: TouchPoint | None = None

    def __post_init__(self) -> None:
        if self.mask is not None and self.touch is not None:
            raise ValueError("passo não pode ter mask e touch ao mesmo tempo")
