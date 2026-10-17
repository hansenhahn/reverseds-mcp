"""Generic IO register decode: the register types and their self-decoding."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegField:
    """A bitfield: name, inclusive bit range and optional value names."""

    name: str
    low: int
    high: int
    values: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True, slots=True)
class DecodedField:
    """A decoded bitfield: name, value and its meaning when the schema names it."""

    name: str
    value: int
    meaning: str | None


@dataclass(frozen=True, slots=True)
class DecodedRegister:
    """A decoded register: raw value plus the named fields."""

    name: str
    address: int
    size: int
    raw: int
    fields: tuple[DecodedField, ...]


@dataclass(frozen=True, slots=True)
class Register:
    """A memory-mapped register: name, address, size and bitfields."""

    name: str
    address: int
    size: int
    fields: tuple[RegField, ...]

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
            decoded.append(DecodedField(spec.name, value, meaning))
        return DecodedRegister(self.name, self.address, self.size, raw, tuple(decoded))


class UnknownRegister(ValueError):
    """The address is not covered by the IO schema."""
