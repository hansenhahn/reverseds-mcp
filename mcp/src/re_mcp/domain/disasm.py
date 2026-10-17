"""Desassemblagem ARM/Thumb (domínio puro, sem I/O).

Usa `capstone`. Recebe bytes já lidos (a leitura de memória é responsabilidade do
adaptador), de modo que o domínio fica testável sem o emulador.
"""
from dataclasses import dataclass

from capstone import CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB, Cs

_MODES = {"arm": CS_MODE_ARM, "thumb": CS_MODE_THUMB}


@dataclass(frozen=True, slots=True)
class Instruction:
    """Uma instrução desmontada."""

    address: int
    size: int
    bytes_hex: str
    mnemonic: str
    op_str: str


def disassemble(
    code: bytes, addr: int, mode: str = "arm", count: int | None = None
) -> list[Instruction]:
    """Desmonta ``code`` (a partir de ``addr``) no modo ``arm`` ou ``thumb``.

    Parameters:
        code (bytes): Bytes do código.
        addr (int): Endereço da primeira instrução.
        mode (str): ``arm`` ou ``thumb`` (default ``arm``).
        count (int | None): Máximo de instruções (None = todas as que couberem).

    Returns:
        list[Instruction]: As instruções, em ordem.

    Raises:
        ValueError: Se o modo for inválido.
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
