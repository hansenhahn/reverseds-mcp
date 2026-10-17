"""Application service: read and decode IO registers (over the Debugger port)."""
from ..domain.io import DecodedRegister, UnknownRegister, decode_io, register_at
from .ports import Debugger


class IoReader:
    """Service: read IO registers through the Debugger and decode them."""

    def __init__(self, debugger: Debugger) -> None:
        """Build the service over a debug backend.

        Parameters:
            debugger (Debugger): A connected debug backend.
        """
        self._debugger = debugger

    def read(self, addr: int) -> DecodedRegister:
        """Read and decode the IO register at ``addr``.

        Parameters:
            addr (int): The IO address (e.g. ``0x04000000`` for DISPCNT A).

        Returns:
            DecodedRegister: The decoded register.

        Raises:
            UnknownRegister: If the address is not covered by the schema.
        """
        register = register_at(addr)
        if register is None:
            raise UnknownRegister(f"endereço não é IO mapeado no schema: 0x{addr:08x}")
        decoded = decode_io(addr, self._debugger.read_memory(addr, register.size))
        assert decoded is not None
        return decoded
