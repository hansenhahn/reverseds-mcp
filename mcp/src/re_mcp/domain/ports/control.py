"""Porta do canal de controle do melonDS (JSON-RPC sobre Unix socket)."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class ControlChannel(Protocol):
    """Porta para o canal de controle do melonDS (JSON-RPC sobre Unix socket)."""

    def call(self, method: str, params: dict | None = None) -> dict:
        """Chama um método do canal de controle e devolve o `result`.

        Parameters:
            method (str): Nome do método (ex.: ``ping``, ``input.key``).
            params (dict | None): Parâmetros do método.

        Returns:
            dict: O campo ``result`` da resposta JSON-RPC.

        Raises:
            ControlError: Quando o servidor responde com erro ou a conexão falha.
        """
        ...

    def read_message(self, timeout: float) -> dict | None:
        """Lê a próxima mensagem (resposta ou notificação), ou None no timeout.

        Parameters:
            timeout (float): Timeout de leitura em segundos.

        Returns:
            dict | None: A mensagem recebida, ou None.
        """
        ...

    def close(self) -> None:
        """Fecha a conexão com o canal de controle."""
        ...
