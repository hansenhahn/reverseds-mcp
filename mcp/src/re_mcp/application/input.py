"""Serviço de aplicação: macros de input (tap/sequência) sobre o canal de controle."""
import time
from collections.abc import Callable

from ..domain.input import MAX_TOTAL_MS, NO_KEY, InputStep
from .ports import ControlChannel


class InputMacros:
    """Serviço: macros de input (tap e sequência) sobre o canal de controle."""

    def __init__(
        self, channel: ControlChannel, sleep: Callable[[float], None] = time.sleep
    ) -> None:
        """Monta o serviço sobre um canal de controle.

        Parameters:
            channel (ControlChannel): Canal de controle conectado.
            sleep (Callable[[float], None]): Injetável para testes.
        """
        self._channel = channel
        self._sleep = sleep

    def tap(self, mask: int, ms: int) -> None:
        """Pressiona ``mask``, espera ``ms`` e solta (sempre solta, mesmo em erro)."""
        self._channel.call("input.key", {"mask": mask})
        try:
            self._sleep(ms / 1000.0)
        finally:
            self._channel.call("input.release")

    def run(self, steps: list[InputStep], max_total_ms: int = MAX_TOTAL_MS) -> None:
        """Executa os passos em ordem; solta o input ao final (mesmo em erro).

        Raises:
            ValueError: Se o tempo total exceder ``max_total_ms``.
        """
        total = sum(step.ms + step.after_ms for step in steps)
        if total > max_total_ms:
            raise ValueError(f"sequência longa demais: {total} ms > {max_total_ms} ms")
        try:
            for step in steps:
                if step.mask is not None and step.mask != NO_KEY:
                    self._channel.call("input.key", {"mask": step.mask})
                    self._sleep(step.ms / 1000.0)
                    self._channel.call("input.release")
                if step.after_ms:
                    self._sleep(step.after_ms / 1000.0)
        finally:
            self._channel.call("input.release")
