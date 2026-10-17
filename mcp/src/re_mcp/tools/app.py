"""Base das tools MCP: servidor, ponte e helpers de erro compartilhados."""
from mcp.server.mcpserver import MCPServer

from ..bridge import Bridge
from ..config import Config
from ..infra.control import ControlError

bridge = Bridge(Config.from_env())
mcp = MCPServer("re-mcp")


def error(exc: Exception, hint: str | None = None) -> dict:
    """Erro padronizado: ``{"error", "hint"?}``.

    Parameters:
        exc (Exception): A causa.
        hint (str | None): Dica opcional.

    Returns:
        dict: O dicionário de erro.
    """
    out: dict = {"error": str(exc)}
    if hint:
        out["hint"] = hint
    return out


def debug_error(exc: Exception) -> dict:
    """Erro do debugger com dica conforme a causa.

    Parameters:
        exc (Exception): A causa.

    Returns:
        dict: O dicionário de erro, com dica quando reconhecemos a causa.
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
    """Chama o canal de controle, convertendo erro em dicionário.

    Parameters:
        method (str): Método do canal de controle.
        params (dict | None): Parâmetros.

    Returns:
        dict: O resultado, ou ``{"error", "hint"?}``.
    """
    try:
        return bridge.control().call(method, params)
    except ControlError as exc:
        return error(
            exc, "Verifique se o melonDS está rodando com o canal de controle habilitado."
        )
