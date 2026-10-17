"""Portas (interfaces) do domínio para os backends do emulador.

O domínio fala com estas abstrações; os adaptadores concretos (infra) as
implementam. Usa `typing.Protocol` (não ABCs), conforme as diretrizes.
"""
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


@runtime_checkable
class Debugger(Protocol):
    """Porta para o backend de debug (gdb conectado ao stub do melonDS)."""

    def connect(self, core: str) -> None:
        """Conecta ao core escolhido (``arm9`` ou ``arm7``).

        Parameters:
            core (str): Core alvo.
        """
        ...

    def read_register(self, name: str) -> int:
        """Lê um registrador pelo nome (ex.: ``pc``).

        Parameters:
            name (str): Nome do registrador.

        Returns:
            int: Valor do registrador.
        """
        ...

    def write_register(self, name: str, value: int) -> None:
        """Escreve um valor num registrador.

        Parameters:
            name (str): Nome do registrador.
            value (int): Valor a escrever.
        """
        ...

    def read_memory(self, addr: int, size: int) -> bytes:
        """Lê ``size`` bytes da memória emulada no endereço ``addr``.

        Parameters:
            addr (int): Endereço.
            size (int): Quantidade de bytes.

        Returns:
            bytes: Os bytes lidos.
        """
        ...

    def write_memory(self, addr: int, data: bytes) -> None:
        """Escreve ``data`` na memória emulada a partir de ``addr``.

        Parameters:
            addr (int): Endereço.
            data (bytes): Bytes a escrever.
        """
        ...

    def set_watchpoint(self, addr: int, kind: str, condition: str | None = None) -> int:
        """Cria um watchpoint de hardware (``write``, ``read`` ou ``access``).

        Parameters:
            addr (int): Endereço vigiado.
            kind (str): Tipo de acesso.
            condition (str | None): Expressão gdb opcional; o gdb só para quando
                ela for verdadeira (filtra por valor).

        Returns:
            int: Número do watchpoint.
        """
        ...

    def set_breakpoint(self, addr: int) -> int:
        """Cria um breakpoint de código no endereço.

        Parameters:
            addr (int): Endereço.

        Returns:
            int: Número do breakpoint.
        """
        ...

    def remove(self, number: int) -> None:
        """Remove um breakpoint/watchpoint pelo número.

        Parameters:
            number (int): Número do breakpoint/watchpoint.
        """
        ...

    def continue_(self, timeout: float = 30.0) -> bool:
        """Retoma a execução e espera a parada.

        Parameters:
            timeout (float): Tempo máximo de espera em segundos.

        Returns:
            bool: True se parou (breakpoint/watchpoint); False se estourou o timeout.
        """
        ...

    def step(self) -> None:
        """Executa uma instrução."""
        ...

    def interrupt(self) -> None:
        """Interrompe a execução."""
        ...

    def resume(self) -> None:
        """Retoma a execução em segundo plano (não bloqueia)."""
        ...

    def wait_stop(self, timeout: float) -> bool:
        """Espera a parada do `continue` de fundo.

        Parameters:
            timeout (float): Tempo máximo de espera em segundos.

        Returns:
            bool: True se parou; False se ainda está rodando.
        """
        ...

    def is_running(self) -> bool:
        """True se o alvo está executando (continue de fundo ativo)."""
        ...

    def disconnect(self) -> None:
        """Desconecta do alvo — o emulador volta a rodar."""
        ...

    def close(self) -> None:
        """Encerra o backend de debug."""
        ...
