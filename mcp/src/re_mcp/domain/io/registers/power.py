"""Power register definitions: POWCNT1."""
from ..decode import Register, RegField


def power_registers() -> list[Register]:
    """The power/graphics-enable registers.

    Returns:
        list[Register]: POWCNT1.
    """
    powcnt1 = (
        RegField.bit("lcd_enable", 0, (), "Enable both LCDs"),
        RegField.bit("engine_a_2d", 1, (), "2D graphics engine A"),
        RegField.bit("engine_3d_render", 2, (), "3D rendering engine"),
        RegField.bit("engine_3d_geometry", 3, (), "3D geometry engine"),
        RegField.bit("engine_b_2d", 9, (), "2D graphics engine B"),
        RegField.bit("display_swap", 15, ((0, "A to lower"), (1, "A to upper")),
                     "Display swap (which engine goes to the top screen)"),
    )
    return [Register("POWCNT1", 0x04000304, 2, powcnt1, "Graphics power control")]
