"""Application service: validate a function contract at runtime."""
from ..domain.contract import Contract, ContractHit, ReturnHit
from .args import ArgsOnHit
from .ports import Debugger

_REGS = ("r0", "r1", "r2", "r3", "sp", "lr", "cpsr")
_MAX_HITS = 32


class ContractChecks:
    """Service: capture a callsite and check args, optionally the first return."""

    def __init__(self, debugger: Debugger) -> None:
        """Build the service."""
        self._debugger = debugger

    def run(
        self,
        addr: int,
        contract: Contract,
        condition: str | None = None,
        count: int = 1,
        timeout: float = 30.0,
        stack_words: int = 8,
    ) -> list[ContractHit]:
        """Check up to ``count`` invocations of ``addr`` against ``contract``."""
        count = max(1, min(count, _MAX_HITS))
        if not contract.returns_expected:
            hits = ArgsOnHit(self._debugger).collect(
                addr,
                condition,
                count,
                timeout,
                stack_words,
                contract=contract,
            )
            return [ContractHit(entry=hit) for hit in hits]

        results: list[ContractHit] = []
        for _ in range(count):
            hits = ArgsOnHit(self._debugger).collect(
                addr,
                condition,
                1,
                timeout,
                stack_words,
                contract=contract,
            )
            if not hits:
                break
            returned = self._capture_return(contract, timeout)
            results.append(
                ContractHit(entry=hits[0], returned=returned, returns_expected=True)
            )
        return results

    def _capture_return(self, contract: Contract, timeout: float) -> ReturnHit | None:
        """Stop at ``lr`` after the call and check the return registers."""
        try:
            lr = self._debugger.read_register("lr")
        except RuntimeError:
            return None
        if lr in (0, 0xFFFFFFFF):
            return None
        try:
            number = self._debugger.set_breakpoint(lr & ~1)
        except RuntimeError:
            return None
        try:
            if not self._debugger.continue_(timeout):
                return None
            registers = {
                name: self._debugger.read_register(name) for name in _REGS
            }
            return ReturnHit(registers, contract.check_returns(registers))
        finally:
            try:
                self._debugger.remove(number)
            except Exception:  # noqa: BLE001 - best effort cleanup
                pass
