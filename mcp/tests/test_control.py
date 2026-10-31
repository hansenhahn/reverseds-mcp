"""Control-channel client robustness tests (framing, id-matching, reconnect)."""
import json
import socket
import threading

import pytest

from re_mcp.infra.control import ControlError, UnixControlChannel


def _channel(sock: socket.socket) -> UnixControlChannel:
    """Bind a channel to an existing socket (bypassing the connect to a path)."""
    channel = UnixControlChannel.__new__(UnixControlChannel)
    channel._path = "/nonexistent"  # noqa: SLF001 - test seam for a fake transport
    channel._timeout = 1.0
    channel._sock = sock
    channel._id = 0
    channel._pending = []
    channel._lock = threading.RLock()  # noqa: SLF001 - test seam (skips __init__)
    return channel


def _frame(payload: dict) -> bytes:
    body = json.dumps(payload).encode()
    return b"Content-Length: %d\r\n\r\n" % len(body) + body


def test_call_matches_id_and_buffers_notifications() -> None:
    """A notification before the response is buffered, not mistaken for the reply."""
    a, b = socket.socketpair()
    channel = _channel(a)
    b.sendall(_frame({"jsonrpc": "2.0", "method": "event.dma", "params": {"transfers": []}}))
    b.sendall(_frame({"jsonrpc": "2.0", "id": 1, "result": {"pong": True}}))
    assert channel.call("ping") == {"pong": True}
    queued = channel.read_message(0.0)
    assert queued is not None and queued["method"] == "event.dma"
    a.close()
    b.close()


def test_empty_body_is_transport_error() -> None:
    """A truncated/empty message is a transport error (reconnect), not a desync."""
    a, b = socket.socketpair()
    channel = _channel(a)
    b.sendall(b"Content-Length: 0\r\n\r\n")
    with pytest.raises(ControlError):
        channel.call("ping")
    a.close()
    b.close()


def test_call_reads_binary_payload() -> None:
    """A response announcing a binary payload is followed by the raw bytes."""
    a, b = socket.socketpair()
    channel = _channel(a)
    b.sendall(_frame({"jsonrpc": "2.0", "id": 1, "result": {"binary": {"bytes": 4}}}))
    b.sendall((4).to_bytes(4, "big") + b"DATA")
    result = channel.call("rom.read", {"offset": 0, "size": 4})
    assert result["binary"]["data"] == b"DATA"
    a.close()
    b.close()


def test_error_response_is_control_error() -> None:
    """A JSON-RPC error response raises ControlError with the server message."""
    a, b = socket.socketpair()
    channel = _channel(a)
    b.sendall(
        _frame({"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "boom"}})
    )
    with pytest.raises(ControlError, match="boom"):
        channel.call("ping")
    a.close()
    b.close()
