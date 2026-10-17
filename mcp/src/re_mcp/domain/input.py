"""Macros de input (domínio): tap e sequência sobre a porta `ControlChannel`.

O domínio não faz I/O direto: fala com a porta ``ControlChannel`` e recebe o
"dorminhoco" (`sleep`) injetado, para ser testável sem o emulador.
"""
import time
from collections.abc import Callable
from dataclasses import dataclass

from .ports import ControlChannel

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


def tap(channel: ControlChannel, mask: int, ms: int, sleep: Callable[[float], None] = time.sleep) -> None:
    """Pressiona ``mask``, espera ``ms`` e solta (sempre solta, mesmo em erro)."""
    channel.call("input.key", {"mask": mask})
    try:
        sleep(ms / 1000.0)
    finally:
        channel.call("input.release")


def sequence(
    channel: ControlChannel,
    steps: list[InputStep],
    sleep: Callable[[float], None] = time.sleep,
    max_total_ms: int = MAX_TOTAL_MS,
) -> None:
    """Executa uma lista de passos em ordem; solta o input ao final (mesmo em erro).

    Raises:
        ValueError: Se o tempo total exceder ``max_total_ms``.
    """
    total = sum(step.ms + step.after_ms for step in steps)
    if total > max_total_ms:
        raise ValueError(f"sequência longa demais: {total} ms > {max_total_ms} ms")
    try:
        for step in steps:
            if step.mask is not None and step.mask != NO_KEY:
                channel.call("input.key", {"mask": step.mask})
                sleep(step.ms / 1000.0)
                channel.call("input.release")
            if step.after_ms:
                sleep(step.after_ms / 1000.0)
    finally:
        channel.call("input.release")
