"""Modelo de depuração: alvos de watchpoint e diff de memória (puro)."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WatchpointHit:
    """Parada de watchpoint: PC e contexto de registradores."""

    pc: int
    registers: dict[str, int]


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Um bloco de memória guardado, com seu endereço base."""

    addr: int
    data: bytes


@dataclass(frozen=True, slots=True)
class MemoryChange:
    """Um byte que mudou entre dois estados."""

    addr: int
    old: int
    new: int


@dataclass(frozen=True, slots=True)
class MemoryDiff:
    """Comparação de dois blocos de memória de mesmo tamanho."""

    changes: tuple[MemoryChange, ...]

    @classmethod
    def between(cls, before: bytes, after: bytes, base: int) -> "MemoryDiff":
        """Compara dois blocos e lista os bytes que mudaram.

        Parameters:
            before (bytes): Bloco anterior.
            after (bytes): Bloco atual.
            base (int): Endereço base do bloco.

        Returns:
            MemoryDiff: As mudanças ``(addr, old, new)``.
        """
        return cls(
            tuple(
                MemoryChange(base + offset, old, new)
                for offset, (old, new) in enumerate(zip(before, after))
                if old != new
            )
        )

    def __len__(self) -> int:
        return len(self.changes)
