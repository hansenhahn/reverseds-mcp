"""Adapter for the melonDS control channel (JSON-RPC over a Unix socket)."""
import json
import socket

from ..application.ports import ControlChannel


class ControlError(RuntimeError):
    """Control-channel error (JSON-RPC error response or connection failure)."""


class _TransportError(ConnectionError):
    """Transport failure (dead socket); triggers automatic reconnection."""


class UnixControlChannel(ControlChannel):
    """Control-channel client (``Content-Length`` framing + JSON-RPC 2.0).

    Supports the binary frame ``[u32 BE N][bytes]`` that follows responses/notifications
    announcing a binary payload (e.g. screen capture).

    Robustness:

    - a ``call`` matches the response by ``id``; notifications (``event.*``) that arrive in
      the meantime are queued for ``read_message`` instead of desyncing the stream;
    - a dead socket, a truncated/empty body or undecodable JSON all trigger a reconnect;
    - a **timeout** is surfaced as an error (never silently retried, which would re-execute
      a non-idempotent operation such as a frame step).
    """

    def __init__(self, socket_path: str, timeout: float = 5.0) -> None:
        """Store the configuration and open the initial connection.

        Parameters:
            socket_path (str): Path to the melonDS Unix socket.
            timeout (float): Default read timeout in seconds.

        Raises:
            ControlError: If it cannot connect.
        """
        self._path = socket_path
        self._timeout = timeout
        self._sock: socket.socket | None = None
        self._id = 0
        self._pending: list[dict] = []
        self._connect()

    def _connect(self) -> None:
        """Open (or reopen) the connection to the control-channel socket.

        Raises:
            ControlError: If it cannot connect.
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
        """Close the current socket and open a new one, swallowing failures."""
        self.close()
        try:
            self._connect()
        except ControlError:
            self._sock = None

    def reset(self) -> None:
        """Force a fresh connection (drops any queued notifications)."""
        self._pending.clear()
        self._reconnect()
        if self._sock is None:
            raise ControlError(f"não reconectou em {self._path}")

    def call(self, method: str, params: dict | None = None, timeout: float | None = None) -> dict:
        """Call a control-channel method and return the ``result``.

        Parameters:
            method (str): Method name.
            params (dict | None): Parameters.
            timeout (float | None): Read timeout for this call (defaults to the channel's).

        Returns:
            dict: The response ``result`` field (with ``binary.data`` when present).

        Raises:
            ControlError: On a JSON-RPC error response, a timeout or a connection error.
        """
        self._id += 1
        request: dict = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            request["params"] = params
        body = json.dumps(request).encode()

        message: dict | None = None
        last: Exception | None = None
        for _ in range(2):
            try:
                self._send(body)
                message = self._await_response(self._id, timeout)
                break
            except TimeoutError as exc:
                # the request was sent; do NOT retry (the operation may be running)
                raise ControlError(f"{method}: timeout") from exc
            except (OSError, _TransportError, ValueError) as exc:
                last = exc
                self._reconnect()
        if message is None:
            raise ControlError(f"{method}: falha de conexão ({last})")

        if "error" in message:
            error = message["error"]
            raise ControlError(f"{method}: {error.get('message', error)}")
        return message.get("result", {})

    def read_message(self, timeout: float) -> dict | None:
        """Read the next message (queued notification or fresh), or None on timeout.

        Parameters:
            timeout (float): Read timeout in seconds.

        Returns:
            dict | None: The message, or None if nothing arrived in time.
        """
        if self._pending:
            return self._pending.pop(0)
        if self._sock is None:
            return None
        try:
            return self._recv_message(timeout)
        except TimeoutError:
            return None
        except (OSError, _TransportError, ValueError) as exc:
            raise ControlError(f"conexão encerrada: {exc}") from exc

    def close(self) -> None:
        """Close the connection."""
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def _await_response(self, expected_id: int, timeout: float | None) -> dict:
        """Read messages until the response with ``expected_id`` arrives.

        Notifications (no matching ``id``) are queued for ``read_message``.
        """
        while True:
            message = self._recv_message(timeout)
            if message.get("id") == expected_id:
                return message
            self._pending.append(message)

    def _send(self, body: bytes) -> None:
        if self._sock is None:
            raise _TransportError("canal não conectado")
        self._sock.sendall(b"Content-Length: %d\r\n\r\n" % len(body) + body)

    def _recv_message(self, timeout: float | None) -> dict:
        previous: float | None = None
        if self._sock is None:
            raise _TransportError("canal não conectado")
        if timeout is not None:
            previous = self._sock.gettimeout()
            self._sock.settimeout(timeout)
        try:
            message = self._recv()
            for container in (message.get("result"), message.get("params")):
                if isinstance(container, dict) and "binary" in container:
                    size = int.from_bytes(self._recv_exact(4), "big")
                    container["binary"]["data"] = self._recv_exact(size)
                    break
            return message
        finally:
            if previous is not None and self._sock is not None:
                self._sock.settimeout(previous)

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
        if not body:
            raise _TransportError("mensagem vazia (canal dessincronizado)")
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
