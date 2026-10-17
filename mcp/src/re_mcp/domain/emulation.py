"""Emulação: macros de input e trace de cartucho (domínio, sobre a porta ControlChannel)."""
import time
from collections.abc import Callable
from dataclasses import dataclass

from .ports import CartFs, ControlChannel

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


class InputMacros:
    """Serviço: macros de input (tap e sequência) sobre o canal de controle."""

    def __init__(
        self, channel: ControlChannel, sleep: Callable[[float], None] = time.sleep
    ) -> None:
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


class TraceError(RuntimeError):
    """Erro ao iniciar o trace de cartucho."""


class CartTrace:
    """Serviço: trace de leitura do cartucho sobre o canal de controle."""

    def __init__(
        self, channel: ControlChannel, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._channel = channel
        self._clock = clock

    def start(self, batch: int = 256, timeout_ms: int = 100) -> dict:
        """Inicia o trace de leitura do cartucho.

        Returns:
            dict: O resultado do canal de controle.
        """
        return self._channel.call(
            "cart.trace.start", {"batch": batch, "timeout_ms": timeout_ms}
        )

    def stop(self) -> dict:
        """Para o trace de leitura do cartucho.

        Returns:
            dict: O resultado do canal de controle.
        """
        return self._channel.call("cart.trace.stop")

    def collect(self, seconds: float) -> list[dict]:
        """Coleta as leituras recebidas (lotes ``event.cart``) por ``seconds``.

        Parameters:
            seconds (float): Duração da coleta em segundos.

        Returns:
            list[dict]: As leituras ``{addr, length, command}`` coletadas.
        """
        reads: list[dict] = []
        deadline = self._clock() + seconds
        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                break
            message = self._channel.read_message(timeout=min(0.5, remaining))
            if message is not None and message.get("method") == "event.cart":
                reads.extend(message["params"]["reads"])
        return reads

    def by_file(
        self, seconds: float, fs: CartFs, batch: int = 256, timeout_ms: int = 100
    ) -> dict[str, int]:
        """Inicia o trace, coleta por ``seconds`` e agrega por arquivo do FS.

        Parameters:
            seconds (float): Duração da coleta.
            fs (CartFs): O filesystem usado para traduzir offsets em arquivos.
            batch (int): Itens por lote.
            timeout_ms (int): Timeout do lote em milissegundos.

        Returns:
            dict[str, int]: Contagem por caminho (``<não-arquivo>`` para offsets fora do FS).

        Raises:
            TraceError: Se o trace não iniciar.
        """
        started = self.start(batch, timeout_ms)
        if "error" in started:
            raise TraceError(str(started["error"]))
        try:
            reads = self.collect(seconds)
        finally:
            self.stop()
        files: dict[str, int] = {}
        for read in reads:
            path = fs.file_for_offset(read["addr"]) or "<não-arquivo>"
            files[path] = files.get(path, 0) + 1
        return files
