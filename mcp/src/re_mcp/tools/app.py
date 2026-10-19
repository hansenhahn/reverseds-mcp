"""Base for the MCP tools: server, bridge and shared error helpers."""
import io
import logging
import time
from typing import Any

from mcp.server.mcpserver import MCPServer
from PIL import Image

from ..bridge import Bridge
from ..config import Config
from ..domain.io import DecodedRegister
from ..infra.control import ControlError

bridge = Bridge(Config.from_env())
log = logging.getLogger("re_mcp")


class _ToolLogMiddleware:
    """Log every ``tools/call`` with the tool name, duration and ok/error."""

    async def __call__(self, ctx: Any, call_next: Any) -> Any:
        if getattr(ctx, "method", None) != "tools/call":
            return await call_next(ctx)
        params = getattr(ctx, "params", None) or {}
        name = params.get("name") if isinstance(params, dict) else None
        started = time.monotonic()
        try:
            result = await call_next(ctx)
        except Exception as exc:  # noqa: BLE001 - log then re-raise
            log.error("tool=%s error=%s dur=%.0fms", name, exc, (time.monotonic() - started) * 1000)
            raise
        status = "error" if getattr(result, "isError", False) else "ok"
        log.info("tool=%s %s dur=%.0fms", name, status, (time.monotonic() - started) * 1000)
        return result


mcp = MCPServer("re-mcp", middleware=[_ToolLogMiddleware()])


def reg_dict(register: DecodedRegister) -> dict:
    """Serialize a decoded IO register for a tool response.

    Parameters:
        register (DecodedRegister): The decoded register.

    Returns:
        dict: The serialized register.
    """
    return {
        "name": register.name,
        "address": f"0x{register.address:08x}",
        "raw": f"0x{register.raw:x}",
        "description": register.description,
        "fields": {
            f.name: {"value": f.value, "meaning": f.meaning, "description": f.description}
            for f in register.fields
        },
    }


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


def control_call(
    method: str, params: dict | None = None, timeout: float | None = None
) -> dict:
    """Call the control channel, turning errors into a dictionary.

    Parameters:
        method (str): Control-channel method.
        params (dict | None): Parameters.
        timeout (float | None): Read timeout for this call (defaults to the channel's).

    Returns:
        dict: The result, or ``{"error", "hint"?}``.
    """
    try:
        return bridge.control().call(method, params, timeout=timeout)
    except ControlError as exc:
        return error(
            exc, "Verifique se o melonDS está rodando com o canal de controle habilitado."
        )


def save_framebuffer_pngs(
    result: dict, *, format: str, prefix: str
) -> dict:
    """Encode a control-channel framebuffer result into PNG files.

    Parameters:
        result (dict): A ``result`` dict holding a ``binary`` payload (width, height, data).
        format (str): ``rgba8`` or ``bgra8``.
        prefix (str): File name prefix; an index suffix is appended per screen.

    Returns:
        dict: ``{"paths": [...]}`` with the saved PNGs.
    """
    binary = result.get("binary", {})
    data = binary.get("data", b"")
    width = binary.get("width", 256)
    height = binary.get("height", 192)
    raw_mode = "RGBA" if format == "rgba8" else "BGRA"
    frame = width * height * 4
    paths: list[str] = []
    for index in range(len(data) // frame):
        image = Image.frombuffer(
            "RGBA", (width, height),
            data[index * frame:(index + 1) * frame],
            "raw", raw_mode, 0, 1,
        )
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        paths.append(bridge.files().write_bytes(f"{prefix}_{index}.png", buffer.getvalue()))
    return {"paths": paths}
