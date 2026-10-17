"""DMA register definitions — GBATEK "DMACNT"."""
from ..decode import Register
from ._fields import bit, bits


def dma_registers() -> list[Register]:
    """The DMA control registers (channels 0..3).

    Returns:
        list[Register]: DMA0CNT..DMA3CNT.
    """
    dmacnt = (
        bits("word_count", 0, 20, (), "Word count"),
        bits("dest_control", 21, 22,
             ((0, "inc"), (1, "dec"), (2, "fixed"), (3, "inc/reload")),
             "Destination address control"),
        bits("src_control", 23, 24, ((0, "inc"), (1, "dec"), (2, "fixed")),
             "Source address control"),
        bit("repeat", 25, (), "Repeat (1=do not reload)"),
        bit("transfer_32bit", 26, (), "Transfer size (0=16-bit, 1=32-bit)"),
        bits("start_timing", 27, 29,
             ((0, "immediately"), (1, "v-blank"), (2, "h-blank"), (3, "display sync"),
              (4, "main memory display"), (5, "cart slot"), (6, "gba slot"), (7, "geometry fifo")),
             "Start timing"),
        bit("irq", 30, (), "IRQ on end"),
        bit("enable", 31, (), "DMA enable"),
    )
    return [
        Register(f"DMA{i}CNT", 0x040000B8 + 12 * i, 4, dmacnt, f"DMA control (channel {i})")
        for i in range(4)
    ]
