"""The IO register map: lookup and decode. Built explicitly, not at import."""
from collections.abc import Iterable

from .decode import DecodedRegister, Register
from .registers import default_registers


class IoMap:
    """The set of known IO registers, indexed by address."""

    def __init__(self, registers: Iterable[Register]) -> None:
        """Index the registers by address.

        Parameters:
            registers (Iterable[Register]): The register definitions.
        """
        self._by_addr = {register.address: register for register in registers}

    @classmethod
    def default(cls) -> "IoMap":
        """Build the map with the registers defined by the schema.

        Returns:
            IoMap: The default IO map.
        """
        return cls(default_registers())

    def register_at(self, addr: int) -> Register | None:
        """The register at ``addr``, or None if not covered.

        Parameters:
            addr (int): The IO address.

        Returns:
            Register | None: The register definition, or None.
        """
        return self._by_addr.get(addr)

    def decode(self, addr: int, data: bytes) -> DecodedRegister | None:
        """Decode the register at ``addr`` from ``data``, or None if not covered.

        Parameters:
            addr (int): The IO address.
            data (bytes): The bytes read at that address.

        Returns:
            DecodedRegister | None: The decoded register, or None.
        """
        register = self._by_addr.get(addr)
        return register.decode(data) if register is not None else None
