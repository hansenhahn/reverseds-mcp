"""Decomp snippets: a C+ASM note attached to an address (pure model)."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecompSnippet:
    """A decomp note (C and/or ASM) for an address."""

    addr: int
    c: str | None = None
    asm: str | None = None
