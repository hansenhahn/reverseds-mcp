"""Application service: capture and check arguments at a callsite."""
import struct

from ..domain.addresses import AddressSpace
from ..domain.debug import ArgCheck, ArgHit
from .ports import Debugger

_REGS = ("r0", "r1", "r2", "r3", "sp", "lr", "cpsr")
_MAX_HITS = 32
_MAX_STACK_WORDS = 64


def _is_pointer(value: int) -> bool:
    region = AddressSpace.region_for(value)
    return region is not None and region.name not in {"itcm", "arm9-bios"}


def _matches(expected: int | str, actual: int) -> bool:
    if isinstance(expected, int):
        return actual == expected
    if expected == "ptr":
        return _is_pointer(actual)
    if expected == "nonzero":
        return actual != 0
    if expected == "zero":
        return actual == 0
    return True  # unknown token: reported as unchecked


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
    ) -> list[ArgHit]:
        """Capture up to ``count`` hits at ``addr`` and check the schema."""
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
                checks = self._check(schema, registers, stack)
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

    @staticmethod
    def _check(
        schema: dict[str, int | str] | None,
        registers: dict[str, int],
        stack: tuple[int, ...],
    ) -> tuple[ArgCheck, ...]:
        if not schema:
            return ()
        checks: list[ArgCheck] = []
        for arg, expected in schema.items():
            actual: int | None = registers.get(arg)
            if actual is None and arg.startswith("stack"):
                try:
                    index = int(arg[5:])
                except ValueError:
                    index = -1
                actual = stack[index] if 0 <= index < len(stack) else None
            if actual is None:
                checks.append(ArgCheck(arg, expected, 0, False))
            else:
                checks.append(ArgCheck(arg, expected, actual, _matches(expected, actual)))
        return tuple(checks)
