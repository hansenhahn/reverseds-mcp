"""ARM/Thumb disassembly (pure domain, capstone wrapper).

Receives already-read bytes (memory reading is the adapter's responsibility), so the
domain is testable without the emulator.
"""
from dataclasses import dataclass

from capstone import CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB, Cs

_MODES = {"arm": CS_MODE_ARM, "thumb": CS_MODE_THUMB}


@dataclass(frozen=True, slots=True)
class Instruction:
    """A disassembled instruction."""

    address: int
    size: int
    bytes_hex: str
    mnemonic: str
    op_str: str


class Disassembler:
    """Service: disassembles ARM/Thumb from the code bytes."""

    def disassemble(
        self, code: bytes, addr: int, mode: str = "arm", count: int | None = None
    ) -> list[Instruction]:
        """Disassemble ``code`` (starting at ``addr``) in ``arm`` or ``thumb`` mode.

        Parameters:
            code (bytes): The code bytes.
            addr (int): The address of the first instruction.
            mode (str): ``arm`` or ``thumb`` (default ``arm``).
            count (int | None): Maximum number of instructions (None = all that fit).

        Returns:
            list[Instruction]: The instructions, in order.

        Raises:
            ValueError: If the mode is invalid.
        """
        if mode not in _MODES:
            raise ValueError(f"modo inválido: {mode!r} (use 'arm' ou 'thumb')")
        md = Cs(CS_ARCH_ARM, _MODES[mode])
        out: list[Instruction] = []
        for insn in md.disasm(code, addr):
            out.append(
                Instruction(
                    address=insn.address,
                    size=insn.size,
                    bytes_hex=insn.bytes.hex(),
                    mnemonic=insn.mnemonic,
                    op_str=insn.op_str,
                )
            )
            if count is not None and len(out) >= count:
                break
        return out
