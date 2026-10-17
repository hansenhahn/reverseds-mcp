"""DMA register definitions: DMAxCNT."""
from ..decode import Register
from ._fields import bit, bits


def dma_registers() -> list[Register]:
    """The DMA control registers (channels 0..3).

    Returns:
        list[Register]: DMA0CNT..DMA3CNT.
    """
    dmacnt = (
        bits("word_count", 0, 20),
        bits(
            "dest_control",
            21,
            22,
            ((0, "inc"), (1, "dec"), (2, "fixed"), (3, "inc/reload")),
        ),
        bits("src_control", 23, 24, ((0, "inc"), (1, "dec"), (2, "fixed"))),
        bit("repeat", 25),
        bit("transfer_32bit", 26),
        bits(
            "start_timing",
            27,
            29,
            (
                (0, "immediately"),
                (1, "v-blank"),
                (2, "h-blank"),
                (3, "display sync"),
                (4, "main memory display"),
                (5, "cart slot"),
                (6, "gba slot"),
                (7, "geometry fifo"),
            ),
        ),
        bit("irq", 30),
        bit("enable", 31),
    )
    return [Register(f"DMA{i}CNT", 0x040000B8 + 12 * i, 4, dmacnt) for i in range(4)]
