"""Server error-helper tests (`error`/`debug_error`)."""
from re_mcp.infra.gdb import DebugError
from re_mcp.tools.app import debug_error, error


def test_error_without_hint() -> None:
    """`error` without a hint returns only `{"error"}`."""
    assert error(RuntimeError("boom")) == {"error": "boom"}


def test_error_with_hint() -> None:
    """`error` with a hint includes `hint`."""
    out = error(RuntimeError("boom"), "dica")
    assert out["error"] == "boom"
    assert out["hint"] == "dica"


def test_debug_error_running_hint() -> None:
    """A running target suggests debug_wait/debug_interrupt."""
    out = debug_error(DebugError("alvo em execução: x"))
    assert "debug_wait" in out["hint"]


def test_debug_error_not_connected_hint() -> None:
    """gdb not started suggests debug_connect."""
    out = debug_error(DebugError("gdb não iniciado (chame connect antes)"))
    assert "debug_connect" in out["hint"]


def test_debug_error_generic() -> None:
    """An unknown error does not invent a hint."""
    out = debug_error(DebugError("outra coisa qualquer"))
    assert "hint" not in out
