"""Modelo de input: um passo de sequência e as constantes de máscara."""
from dataclasses import dataclass

# Teto de sanidade para o tempo total de uma sequência (evita trava acidental).
MAX_TOTAL_MS = 60_000

# Máscara active-low "nada pressionado" (a mesma do canal de controle).
NO_KEY = 0xFFF


@dataclass(frozen=True, slots=True)
class InputStep:
    """Um passo de input: aperta ``mask`` por ``ms`` e depois espera ``after_ms``.

    ``mask`` None (ou ``NO_KEY``) significa "apenas esperar".
    """

    ms: int
    after_ms: int = 0
    mask: int | None = None
