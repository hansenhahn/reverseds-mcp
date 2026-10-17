"""Serviço de aplicação: acha quem escreve/lê um endereço (watchpoint + execução)."""
from ..domain.debug import WatchpointHit
from .ports import Debugger

_CONTEXT_REGS = ("r0", "r1", "r2", "r3", "sp", "lr")


class Watchpoints:
    """Serviço: acha quem escreve/lê um endereço (watchpoint + execução)."""

    def __init__(self, debugger: Debugger) -> None:
        """Monta o serviço sobre um backend de debug.

        Parameters:
            debugger (Debugger): Backend de debug conectado.
        """
        self._debugger = debugger

    def find_write(
        self, addr: int, timeout: float = 30.0, condition: str | None = None
    ) -> WatchpointHit | None:
        """Acha o código que escreve em ``addr`` (watchpoint de escrita + run)."""
        return self._find(addr, "write", timeout, condition)

    def find_read(
        self, addr: int, timeout: float = 30.0, condition: str | None = None
    ) -> WatchpointHit | None:
        """Acha o código que lê ``addr`` (watchpoint de leitura + run)."""
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
