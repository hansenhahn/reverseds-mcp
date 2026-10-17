"""IO register definitions, grouped by subsystem."""
from ..decode import Register
from .dma import dma_registers
from .power import power_registers
from .video import video_registers
from .vram_banks import vram_registers


def default_registers() -> list[Register]:
    """All IO registers covered by the schema.

    Returns:
        list[Register]: The registers from every subsystem.
    """
    return [*video_registers(), *power_registers(), *dma_registers(), *vram_registers()]
