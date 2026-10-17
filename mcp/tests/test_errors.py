"""Testes dos helpers de erro do servidor (`_error`/`_debug_error`)."""
from re_mcp.infra.gdb import DebugError
from re_mcp.tools import server


def test_error_without_hint() -> None:
    """`_error` sem dica devolve só `{"error"}`."""
    assert server._error(RuntimeError("boom")) == {"error": "boom"}


def test_error_with_hint() -> None:
    """`_error` com dica inclui `hint`."""
    out = server._error(RuntimeError("boom"), "dica")
    assert out["error"] == "boom"
    assert out["hint"] == "dica"


def test_debug_error_running_hint() -> None:
    """Alvo em execução sugere debug_wait/debug_interrupt."""
    out = server._debug_error(DebugError("alvo em execução: x"))
    assert "debug_wait" in out["hint"]


def test_debug_error_not_connected_hint() -> None:
    """gdb não iniciado sugere debug_connect."""
    out = server._debug_error(DebugError("gdb não iniciado (chame connect antes)"))
    assert "debug_connect" in out["hint"]


def test_debug_error_generic() -> None:
    """Erro desconhecido não inventa hint."""
    out = server._debug_error(DebugError("outra coisa qualquer"))
    assert "hint" not in out
