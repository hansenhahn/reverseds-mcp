"""Tipos do domínio."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WatchpointHit:
    """Parada de watchpoint: PC e contexto de registradores."""

    pc: int
    registers: dict[str, int]


@dataclass(frozen=True, slots=True)
class Symbol:
    """Símbolo: um nome para um endereço."""

    addr: int
    name: str
