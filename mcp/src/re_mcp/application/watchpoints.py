"""Application service: find what writes/reads an address (watchpoint + execution)."""
from ..domain.debug import HardwareSlots, WatchpointHit
from .ports import Debugger

_CONTEXT_REGS = ("r0", "r1", "r2", "r3", "sp", "lr")


class Watchpoints:
    """Service: find what writes/reads an address (watchpoint + execution)."""

    def __init__(self, debugger: Debugger) -> None:
        """Build the service over a debug backend.

        Parameters:
            debugger (Debugger): A connected debug backend.
        """
        self._debugger = debugger

    def slots(self) -> HardwareSlots:
        """Report hardware watchpoint usage of the connected core."""
        return HardwareSlots(
            core=self._debugger.core(),
            limit=self._debugger.watchpoint_limit(),
            breakpoints=tuple(self._debugger.breakpoints()),
        )

    def find_write(
        self, addr: int, timeout: float = 30.0, condition: str | None = None
    ) -> WatchpointHit | None:
        """Find the code that writes to ``addr`` (write watchpoint + run)."""
        return self._find(addr, "write", timeout, condition)

    def find_read(
        self, addr: int, timeout: float = 30.0, condition: str | None = None
    ) -> WatchpointHit | None:
        """Find the code that reads ``addr`` (read watchpoint + run)."""
        return self._find(addr, "read", timeout, condition)

    def _find(
        self, addr: int, kind: str, timeout: float, condition: str | None
    ) -> WatchpointHit | None:
        number = self._debugger.set_watchpoint(addr, kind, condition)
        try:
            if not self._debugger.continue_(timeout):
                return None
            pc = self._debugger.read_register("pc")
            registers = {
                name: self._debugger.read_register(name) for name in _CONTEXT_REGS
            }
            return WatchpointHit(pc=pc, registers=registers)
        finally:
            self._debugger.remove(number)
