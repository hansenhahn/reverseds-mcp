"""Generic IO register decode: the register types and their self-decoding."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegField:
    """A bitfield: name, inclusive bit range, optional value names and a description."""

    name: str
    low: int
    high: int
    values: tuple[tuple[int, str], ...] = ()
    description: str = ""


@dataclass(frozen=True, slots=True)
class DecodedField:
    """A decoded bitfield: name, value, named meaning and human description."""

    name: str
    value: int
    meaning: str | None
    description: str


@dataclass(frozen=True, slots=True)
class DecodedRegister:
    """A decoded register: raw value, named fields and the register description."""

    name: str
    address: int
    size: int
    raw: int
    fields: tuple[DecodedField, ...]
    description: str = ""


@dataclass(frozen=True, slots=True)
class Register:
    """A memory-mapped register: name, address, size, bitfields and a description."""

    name: str
    address: int
    size: int
    fields: tuple[RegField, ...]
    description: str = ""

    def decode(self, data: bytes) -> DecodedRegister:
        """Decode this register from the bytes read at its address.

        Parameters:
            data (bytes): The bytes read at the register's address.

        Returns:
            DecodedRegister: The decoded register.
        """
        raw = int.from_bytes(data[: self.size], "little")
        decoded: list[DecodedField] = []
        for spec in self.fields:
            width = spec.high - spec.low + 1
            value = (raw >> spec.low) & ((1 << width) - 1)
            meaning = dict(spec.values).get(value) if spec.values else None
            decoded.append(
                DecodedField(spec.name, value, meaning, spec.description)
            )
        return DecodedRegister(
            self.name, self.address, self.size, raw, tuple(decoded), self.description
        )


class UnknownRegister(ValueError):
    """The address is not covered by the IO schema."""
