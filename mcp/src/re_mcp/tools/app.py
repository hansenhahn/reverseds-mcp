"""Base for the MCP tools: server, bridge and shared error helpers."""
from mcp.server.mcpserver import MCPServer

from ..bridge import Bridge
from ..config import Config
from ..infra.control import ControlError

bridge = Bridge(Config.from_env())
mcp = MCPServer("re-mcp")


def error(exc: Exception, hint: str | None = None) -> dict:
    """Standardized error: ``{"error", "hint"?}``.

    Parameters:
        exc (Exception): The cause.
        hint (str | None): Optional hint.

    Returns:
        dict: The error dictionary.
    """
    out: dict = {"error": str(exc)}
    if hint:
        out["hint"] = hint
    return out


def debug_error(exc: Exception) -> dict:
    """Debugger error with a hint depending on the cause.

    Parameters:
        exc (Exception): The cause.

    Returns:
        dict: The error dictionary, with a hint when we recognize the cause.
    """
    msg = str(exc)
    if "alvo em execução" in msg:
        return error(exc, "Use debug_wait() ou debug_interrupt() antes de outros comandos.")
    if "gdb não iniciado" in msg:
        return error(exc, "Chame debug_connect() primeiro.")
    if "falha de conexão" in msg or "não conectou" in msg:
        return error(exc, "O emulador pode ter reiniciado; reconecte (ou reinicie o melonDS).")
    return error(exc)


def control_call(method: str, params: dict | None = None) -> dict:
    """Call the control channel, turning errors into a dictionary.

    Parameters:
        method (str): Control-channel method.
        params (dict | None): Parameters.

    Returns:
        dict: The result, or ``{"error", "hint"?}``.
    """
    try:
        return bridge.control().call(method, params)
    except ControlError as exc:
        return error(
            exc, "Verifique se o melonDS está rodando com o canal de controle habilitado."
        )
