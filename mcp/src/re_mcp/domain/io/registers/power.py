"""Power register definitions: POWCNT1."""
from ..decode import Register
from ._fields import bit


def power_registers() -> list[Register]:
    """The power/graphics-enable registers.

    Returns:
        list[Register]: POWCNT1.
    """
    powcnt1 = (
        bit("lcd_enable", 0),
        bit("engine_a_2d", 1),
        bit("engine_3d_render", 2),
        bit("engine_3d_geometry", 3),
        bit("engine_b_2d", 9),
        bit("display_swap", 15, ((0, "A to lower"), (1, "A to upper"))),
    )
    return [Register("POWCNT1", 0x04000304, 2, powcnt1)]
