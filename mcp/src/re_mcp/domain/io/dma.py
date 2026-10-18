"""Decoded DMA transfers (pure), reusing the GBATEK ``DMAxCNT`` schema."""
from dataclasses import dataclass

from .decode import DecodedRegister
from .registers.dma import dma_registers

# channel -> DMAxCNT register, so a raw Cnt can be decoded by the schema
_DMACNT = {channel: register for channel, register in enumerate(dma_registers())}


@dataclass(frozen=True, slots=True)
class DmaEndpoint:
    """One side of a DMA: its address and address-control mode.

    ``control`` is one of ``inc`` / ``dec`` / ``fixed`` / ``inc/reload``.
    """

    address: int
    control: str


@dataclass(frozen=True, slots=True)
class DmaTransfer:
    """A decoded DMA transfer (from -> to), built from a raw description.

    ``control`` is the decoded ``DMAxCNT`` (same field names as ``io_read``:
    ``transfer_32bit``, ``src_control``, ``dest_control``, ``start_timing``,
    ``repeat``, ``irq``, ``enable``).
    """

    channel: int
    source: DmaEndpoint
    destination: DmaEndpoint
    length: int
    control: DecodedRegister
    pc: int

    @classmethod
    def from_raw(
        cls, channel: int, src: int, dst: int, cnt: int, pc: int
    ) -> "DmaTransfer":
        """Decode a raw DMA description ``{channel, src, dst, cnt, pc}``.

        Parameters:
            channel (int): DMA channel (0..3).
            src (int): Source address (``DMAxSAD``).
            dst (int): Destination address (``DMAxDAD``).
            cnt (int): Raw ``DMAxCNT`` value.
            pc (int): PC that programmed the channel.

        Returns:
            DmaTransfer: The decoded transfer.
        """
        decoded = _DMACNT[channel].decode(cnt.to_bytes(4, "little"))
        fields = {field.name: field for field in decoded.fields}
        size = 4 if fields["transfer_32bit"].value else 2
        return cls(
            channel=channel,
            source=DmaEndpoint(src, fields["src_control"].meaning or "inc"),
            destination=DmaEndpoint(dst, fields["dest_control"].meaning or "inc"),
            length=fields["word_count"].value * size,
            control=decoded,
            pc=pc,
        )
