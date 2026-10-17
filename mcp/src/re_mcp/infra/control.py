"""Adaptador do canal de controle do melonDS (JSON-RPC sobre Unix socket)."""
import json
import socket

from ..application.ports import ControlChannel


class ControlError(RuntimeError):
    """Erro do canal de controle (resposta JSON-RPC de erro ou falha de conexão)."""


class _TransportError(ConnectionError):
    """Falha de transporte (socket morto); dispara reconexão automática."""


class UnixControlChannel(ControlChannel):
    """Cliente do canal de controle (framing ``Content-Length`` + JSON-RPC 2.0).

    Suporta o frame binário ``[u32 BE N][bytes]`` que segue respostas/notificações
    que anunciam um payload binário (ex.: captura de tela).

    A conexão é (re)aberta sob demanda: se o socket morrer (ex.: o melonDS foi
    reiniciado e o socket Unix foi recriado), a próxima chamada reconecta sozinha.
    """

    def __init__(self, socket_path: str, timeout: float = 5.0) -> None:
        """Guarda a configuração e abre a conexão inicial.

        Parameters:
            socket_path (str): Caminho do Unix socket do melonDS.
            timeout (float): Timeout de leitura em segundos.

        Raises:
            ControlError: Se não for possível conectar.
        """
        self._path = socket_path
        self._timeout = timeout
        self._sock: socket.socket | None = None
        self._id = 0
        self._connect()

    def _connect(self) -> None:
        """Abre (ou reabre) a conexão com o socket do canal de controle.

        Raises:
            ControlError: Se não for possível conectar.
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self._timeout)
        try:
            sock.connect(self._path)
        except OSError as exc:
            sock.close()
            raise ControlError(f"não conectou em {self._path}: {exc}") from exc
        self._sock = sock

    def _reconnect(self) -> None:
        """Fecha o socket atual e abre um novo, engolindo falhas."""
        self.close()
        try:
            self._connect()
        except ControlError:
            self._sock = None

    def call(self, method: str, params: dict | None = None) -> dict:
        """Chama um método do canal de controle e devolve o ``result``.

        Reconecta automaticamente uma vez se o socket estiver morto.

        Parameters:
            method (str): Nome do método.
            params (dict | None): Parâmetros.

        Returns:
            dict: O campo ``result`` da resposta (com ``binary.data`` quando houver).

        Raises:
            ControlError: Em erro de resposta JSON-RPC ou de conexão.
        """
        self._id += 1
        request: dict = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            request["params"] = params
        body = json.dumps(request).encode()

        message: dict | None = None
        last: Exception | None = None
        for attempt in range(2):
            try:
                self._send(body)
                message = self._recv_message()
                break
            except (OSError, _TransportError) as exc:
                last = exc
                self._reconnect()
        if message is None:
            raise ControlError(f"{method}: falha de conexão ({last})")

        if "error" in message:
            error = message["error"]
            raise ControlError(f"{method}: {error.get('message', error)}")
        return message.get("result", {})

    def read_message(self, timeout: float) -> dict | None:
        """Lê a próxima mensagem (resposta ou notificação), ou None no timeout.

        Parameters:
            timeout (float): Timeout de leitura em segundos.

        Returns:
            dict | None: A mensagem, ou None se nada chegou no prazo.
        """
        if self._sock is None:
            return None
        previous = self._sock.gettimeout()
        self._sock.settimeout(timeout)
        try:
            return self._recv_message()
        except (TimeoutError, socket.timeout):
            return None
        except (OSError, _TransportError) as exc:
            raise ControlError(f"conexão encerrada: {exc}") from exc
        finally:
            if self._sock is not None:
                self._sock.settimeout(previous)

    def close(self) -> None:
        """Fecha a conexão."""
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def _send(self, body: bytes) -> None:
        if self._sock is None:
            raise _TransportError("canal não conectado")
        self._sock.sendall(b"Content-Length: %d\r\n\r\n" % len(body) + body)

    def _recv_message(self) -> dict:
        message = self._recv()
        for container in (message.get("result"), message.get("params")):
            if isinstance(container, dict) and "binary" in container:
                size = int.from_bytes(self._recv_exact(4), "big")
                container["binary"]["data"] = self._recv_exact(size)
                break
        return message

    def _recv(self) -> dict:
        if self._sock is None:
            raise _TransportError("canal não conectado")
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = self._sock.recv(1)
            if not chunk:
                raise _TransportError("conexão encerrada")
            header += chunk

        length = 0
        for line in header.decode().split("\r\n"):
            if line.lower().startswith("content-length:"):
                length = int(line.split(":", 1)[1].strip())

        body = self._recv_exact(length)
        return json.loads(body)

    def _recv_exact(self, size: int) -> bytes:
        if self._sock is None:
            raise _TransportError("canal não conectado")
        data = b""
        while len(data) < size:
            chunk = self._sock.recv(size - len(data))
            if not chunk:
                raise _TransportError("conexão encerrada no corpo")
            data += chunk
        return data
