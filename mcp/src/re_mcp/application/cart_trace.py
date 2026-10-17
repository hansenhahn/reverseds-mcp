"""Serviço de aplicação: trace de leitura do cartucho sobre o canal de controle."""
import time
from collections.abc import Callable

from .ports import CartFs, ControlChannel


class TraceError(RuntimeError):
    """Erro ao iniciar o trace de cartucho."""


class CartTrace:
    """Serviço: trace de leitura do cartucho sobre o canal de controle."""

    def __init__(
        self, channel: ControlChannel, clock: Callable[[], float] = time.monotonic
    ) -> None:
        """Monta o serviço sobre um canal de controle.

        Parameters:
            channel (ControlChannel): Canal de controle conectado.
            clock (Callable[[], float]): Relógio monotônico (injetável para testes).
        """
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
