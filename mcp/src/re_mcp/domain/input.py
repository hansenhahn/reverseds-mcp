"""Input model: a sequence step and the mask constants."""
from dataclasses import dataclass

# Sanity cap on the total time of a sequence (avoids an accidental hang).
MAX_TOTAL_MS = 60_000

# Active-low "nothing pressed" mask (the same as the control channel).
NO_KEY = 0xFFF


@dataclass(frozen=True, slots=True)
class InputStep:
    """An input step: press ``mask`` for ``ms``, then wait ``after_ms``.

    ``mask`` None (or ``NO_KEY``) means "just wait".
    """

    ms: int
    after_ms: int = 0
    mask: int | None = None
