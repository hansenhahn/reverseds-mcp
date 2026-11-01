"""Static struct-candidate scanning from loads/stores (pure domain)."""
import re
from dataclasses import dataclass

from .disasm import Disassembler

_MEM_RE = re.compile(r"\[(r\d+|sp|pc)(?:,\s*#?(0x[0-9a-fA-F]+|\d+))?\]")
_WIDTHS = {1: "uint8_t", 2: "uint16_t", 4: "uint32_t", 8: "uint64_t"}


@dataclass(frozen=True, slots=True)
class StructField:
    """A candidate field: offset, access width, base registers and hit count."""

    offset: int
    width: int
    registers: tuple[str, ...]
    accesses: int


@dataclass(frozen=True, slots=True)
class StructCandidate:
    """A candidate struct: fields inferred from ``[rN, #imm]`` accesses."""

    fields: tuple[StructField, ...]

    @classmethod
    def scan(
        cls, code: bytes, addr: int, mode: str = "arm"
    ) -> "StructCandidate":
        """Scan ``code`` for ``[rN, #imm]`` loads/stores and group by offset.

        ``sp``/``pc`` bases are ignored. The result is an over-approximation: any
        register may be the struct base, so fields are candidates.
        """
        widths: dict[int, int] = {}
        registers: dict[int, set[str]] = {}
        accesses: dict[int, int] = {}
        for insn in Disassembler().disassemble(code, addr, mode):
            width = cls._access_width(insn.mnemonic)
            if width == 0:
                continue
            for match in _MEM_RE.finditer(insn.op_str):
                base = match.group(1)
                if base in ("sp", "pc"):
                    continue
                text = match.group(2)
                offset = int(text, 0) if text is not None else 0
                widths[offset] = max(widths.get(offset, 0), width)
                registers.setdefault(offset, set()).add(base)
                accesses[offset] = accesses.get(offset, 0) + 1
        return cls(
            fields=tuple(
                StructField(
                    offset=offset,
                    width=width,
                    registers=tuple(sorted(registers[offset])),
                    accesses=accesses[offset],
                )
                for offset, width in sorted(widths.items())
            )
        )

    @staticmethod
    def _access_width(mnemonic: str) -> int:
        if mnemonic in ("ldrb", "strb", "ldrsb", "ldrsbt"):
            return 1
        if mnemonic in ("ldrh", "strh", "ldrsh", "ldrsht"):
            return 2
        if mnemonic in ("ldrd", "strd"):
            return 8
        if mnemonic.startswith("ldr") or mnemonic.startswith("str"):
            return 4
        return 0

    def render_c(self, name: str = "candidate") -> str:
        """Render a C struct skeleton with provisional names and padding."""
        lines = [f"struct {name} {{"]
        cursor = 0
        for field in self.fields:
            if field.offset > cursor:
                lines.append(
                    f"    uint8_t pad_0x{cursor:02x}[0x{field.offset - cursor:x}];"
                )
                cursor = field.offset
            elif field.offset < cursor:
                lines.append(
                    f"    // overlapping access at 0x{field.offset:02x}"
                    f" (width {field.width})"
                )
                continue
            kind = _WIDTHS.get(field.width, "uint8_t")
            registers = ", ".join(field.registers)
            lines.append(
                f"    {kind} field_0x{field.offset:02x};"
                f" // {registers} x{field.accesses}"
            )
            cursor = field.offset + field.width
        lines.append("};")
        return "\n".join(lines)
