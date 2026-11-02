"""Application service: capture and check arguments at a callsite."""
import struct

from ..domain.contract import Contract
from ..domain.debug import ArgHit
from .ports import Debugger

_REGS = ("r0", "r1", "r2", "r3", "sp", "lr", "cpsr")
_MAX_HITS = 32
_MAX_STACK_WORDS = 64


class ArgsOnHit:
    """Service: breakpoint → capture registers/stack → compare with a schema."""

    def __init__(self, debugger: Debugger) -> None:
        """Build the service."""
        self._debugger = debugger

    def collect(
        self,
        addr: int,
        condition: str | None = None,
        count: int = 1,
        timeout: float = 30.0,
        stack_words: int = 8,
        schema: dict[str, int | str] | None = None,
        contract: Contract | None = None,
    ) -> list[ArgHit]:
        """Capture up to ``count`` hits at ``addr`` and check the contract."""
        contract = contract or Contract.from_schema(schema)
        count = max(1, min(count, _MAX_HITS))
        stack_words = max(0, min(stack_words, _MAX_STACK_WORDS))
        if self._debugger.is_running():
            self._debugger.interrupt()
        number = self._debugger.set_breakpoint(addr, condition)
        hits: list[ArgHit] = []
        try:
            for _ in range(count):
                if not self._debugger.continue_(timeout):
                    break
                pc = self._debugger.read_register("pc")
                registers = {
                    name: self._debugger.read_register(name) for name in _REGS
                }
                sp = registers["sp"]
                data = (
                    self._debugger.read_memory(sp, stack_words * 4)
                    if stack_words
                    else b""
                )
                stack = tuple(
                    struct.unpack_from("<I", data, offset)[0]
                    for offset in range(0, len(data) - 3, 4)
                )
                checks = contract.check_args(registers, stack)
                hits.append(
                    ArgHit(
                        pc=pc,
                        registers=registers,
                        stack=stack,
                        checks=checks,
                        ok=all(check.ok for check in checks),
                    )
                )
        finally:
            try:
                self._debugger.remove(number)
            except Exception:  # noqa: BLE001 - best effort cleanup
                pass
        return hits
