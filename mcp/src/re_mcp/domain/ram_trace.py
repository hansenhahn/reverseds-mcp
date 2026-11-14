"""RAM write trace model (pure)."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RamWrite:
    """One CPU data write observed in an address range."""

    cpu: int
    addr: int
    value: int
    width: int
    pc: int

    @classmethod
    def from_raw(cls, raw: dict) -> "RamWrite":
        """Build a write from an ``event.ram`` item.

        Parameters:
            raw (dict): ``{cpu, addr, val, width, pc}`` from the control channel.

        Returns:
            RamWrite: The decoded write.
        """
        return cls(
            cpu=int(raw["cpu"]),
            addr=int(raw["addr"]),
            value=int(raw["val"]),
            width=int(raw["width"]),
            pc=int(raw["pc"]),
        )


@dataclass(frozen=True, slots=True)
class RamWriteGroup:
    """Aggregated CPU writes with the same address/width/PC."""

    cpu: int
    addr: int
    width: int
    pc: int
    count: int
