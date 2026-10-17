"""Application service: read and decode IO registers (over the Debugger port)."""
from ..domain.io import DecodedRegister, IoMap, UnknownRegister
from .ports import Debugger


class IoReader:
    """Service: read IO registers through the Debugger and decode them."""

    def __init__(self, debugger: Debugger, io_map: IoMap) -> None:
        """Build the service.

        Parameters:
            debugger (Debugger): A connected debug backend.
            io_map (IoMap): The IO register map.
        """
        self._debugger = debugger
        self._io_map = io_map

    def read(self, addr: int) -> DecodedRegister:
        """Read and decode the IO register at ``addr``.

        Parameters:
            addr (int): The IO address (e.g. ``0x04000000`` for DISPCNT A).

        Returns:
            DecodedRegister: The decoded register.

        Raises:
            UnknownRegister: If the address is not covered by the schema.
        """
        register = self._io_map.register_at(addr)
        if register is None:
            raise UnknownRegister(f"endereço não é IO mapeado no schema: 0x{addr:08x}")
        decoded = self._io_map.decode(addr, self._debugger.read_memory(addr, register.size))
        assert decoded is not None
        return decoded
