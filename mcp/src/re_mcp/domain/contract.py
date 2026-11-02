"""Function contracts: expected arguments/returns and runtime checks (pure)."""
from dataclasses import dataclass

from .addresses import AddressSpace
from .debug import ArgCheck, ArgHit

_KNOWN = {"ptr", "nonzero", "zero", "any"}
_PREFIXES = ("int:", "hex:", "eq:", "range:", "mask:")


def _is_pointer(value: int) -> bool:
    region = AddressSpace.region_for(value)
    return region is not None and region.name not in {"itcm", "arm9-bios"}


@dataclass(frozen=True, slots=True)
class ArgSpec:
    """One expected argument or return value."""

    name: str
    expected: int | str

    @property
    def checked(self) -> bool:
        """Whether the expectation is a known/validated form."""
        if isinstance(self.expected, int):
            return True
        token = self.expected.strip()
        return token in _KNOWN or token.startswith(_PREFIXES)

    def matches(self, actual: int) -> bool:
        """Whether ``actual`` satisfies this expectation.

        Unknown tokens match (and are reported as unchecked) instead of producing a
        false divergence.
        """
        expected = self.expected
        if isinstance(expected, int):
            return actual == expected
        token = expected.strip()
        if token == "ptr":
            return _is_pointer(actual)
        if token == "nonzero":
            return actual != 0
        if token == "zero":
            return actual == 0
        if token == "any":
            return True
        try:
            if token.startswith(("int:", "hex:", "eq:")):
                return actual == int(token.split(":", 1)[1], 0)
            if token.startswith("range:"):
                low, high = token[6:].split(":", 1)
                return int(low, 0) <= actual <= int(high, 0)
            if token.startswith("mask:"):
                mask, value = token[5:].split(":", 1)
                return (actual & int(mask, 0)) == int(value, 0)
        except ValueError:
            return False
        return True


@dataclass(frozen=True, slots=True)
class Contract:
    """Expected arguments and returns of a callsite."""

    args: tuple[ArgSpec, ...] = ()
    returns: tuple[ArgSpec, ...] = ()

    @classmethod
    def from_schema(
        cls,
        schema: dict[str, int | str] | None,
        ret_schema: dict[str, int | str] | None = None,
    ) -> "Contract":
        """Build a contract from ``{name: expectation}`` mappings."""
        return cls(
            args=tuple(ArgSpec(name, value) for name, value in (schema or {}).items()),
            returns=tuple(
                ArgSpec(name, value) for name, value in (ret_schema or {}).items()
            ),
        )

    @property
    def returns_expected(self) -> bool:
        """Whether the contract asks for a return capture."""
        return bool(self.returns)

    def check_args(
        self, registers: dict[str, int], stack: tuple[int, ...]
    ) -> tuple[ArgCheck, ...]:
        """Check the entry registers/stack against the argument schema."""
        checks: list[ArgCheck] = []
        for spec in self.args:
            actual: int | None = registers.get(spec.name)
            if actual is None and spec.name.startswith("stack"):
                try:
                    index = int(spec.name[5:])
                except ValueError:
                    index = -1
                actual = stack[index] if 0 <= index < len(stack) else None
            checks.append(self._check(spec, actual))
        return tuple(checks)

    def check_returns(self, registers: dict[str, int]) -> tuple[ArgCheck, ...]:
        """Check the return registers against the return schema."""
        return tuple(
            self._check(spec, registers.get(spec.name)) for spec in self.returns
        )

    @staticmethod
    def _check(spec: ArgSpec, actual: int | None) -> ArgCheck:
        if actual is None:
            return ArgCheck(spec.name, spec.expected, 0, False, spec.checked)
        return ArgCheck(
            spec.name,
            spec.expected,
            actual,
            spec.matches(actual),
            spec.checked,
        )


@dataclass(frozen=True, slots=True)
class ReturnHit:
    """A captured return: registers and schema checks."""

    registers: dict[str, int]
    checks: tuple[ArgCheck, ...]

    @property
    def ok(self) -> bool:
        """Whether every return check passed."""
        return all(check.ok for check in self.checks)


@dataclass(frozen=True, slots=True)
class ContractHit:
    """One callsite invocation: entry hit plus optional return hit."""

    entry: ArgHit
    returned: ReturnHit | None = None
    returns_expected: bool = False

    @property
    def ok(self) -> bool:
        """Whether arguments and (when requested) the return match."""
        if not self.returns_expected:
            return self.entry.ok
        return self.entry.ok and self.returned is not None and self.returned.ok
