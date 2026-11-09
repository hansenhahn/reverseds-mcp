"""MCP tools for runtime NitroFS file overrides (asset MITM)."""
from ..application.cart_override import CartOverrideError
from ..infra.control import ControlError
from ..infra.ndsrom import NdsRomError
from .app import bridge, error, mcp


def _override_error(exc: Exception) -> dict:
    """Map an override failure to the tool error contract."""
    if isinstance(exc, CartOverrideError):
        return error(exc, "Confira o caminho com cart_list().")
    if isinstance(exc, NdsRomError):
        return error(exc, "Nenhuma ROM carregada? Confira com rom_info().")
    if isinstance(exc, ControlError):
        return error(
            exc, "Verifique se o melonDS está rodando com o canal de controle habilitado."
        )
    return error(exc)


@mcp.tool()
def cart_override_set(path: str, host_path: str) -> dict:
    """Serve a host file in place of a NitroFS file (runtime override).

    The emulator resolves ``host_path`` in its own filesystem and serves those
    bytes on every cart data read (CPU and DMA) inside the file's ROM range. The
    ROM image on disk is not modified.

    Parameters:
        path (str): File path inside the ROM (e.g. ``/mi/wd/wd_tt``).
        host_path (str): Path of the replacement file, as seen by the emulator.

    Returns:
        dict: ``{"path", "rom_start", "rom_end", "host_size"}`` or
        ``{"error", "hint"?}``.
    """
    try:
        bridge.refresh_rom()
        result = bridge.cart_override().set(path, host_path)
    except (NdsRomError, ControlError, CartOverrideError) as exc:
        return _override_error(exc)
    return {
        "path": path,
        "rom_start": result.get("start"),
        "rom_end": result.get("end"),
        "host_size": result.get("host_size"),
    }


@mcp.tool()
def cart_override_clear(path: str) -> dict:
    """Remove the runtime override of a NitroFS file.

    Parameters:
        path (str): File path inside the ROM.

    Returns:
        dict: ``{"ok": true, "path"}`` or ``{"error", "hint"?}``.
    """
    try:
        bridge.refresh_rom()
        result = bridge.cart_override().clear(path)
    except (NdsRomError, ControlError, CartOverrideError) as exc:
        return _override_error(exc)
    return {"path": path, **result}


@mcp.tool()
def cart_override_list() -> dict:
    """List the runtime overrides registered in the emulator.

    Returns:
        dict: ``{"overrides": [{"start", "end", "host_path", "host_size",
        "hits", "bytes", "loaded"}]}`` or ``{"error", "hint"?}``.
    """
    try:
        result = bridge.cart_override().list()
    except (NdsRomError, ControlError) as exc:
        return _override_error(exc)
    return result


@mcp.tool()
def cart_override_reload(path: str) -> dict:
    """Reread the host file of an override and publish the new content.

    Parameters:
        path (str): File path inside the ROM.

    Returns:
        dict: ``{"ok": true, "path", "host_size"}`` or ``{"error", "hint"?}``.
    """
    try:
        bridge.refresh_rom()
        result = bridge.cart_override().reload(path)
    except (NdsRomError, ControlError, CartOverrideError) as exc:
        return _override_error(exc)
    return {"path": path, **result}


@mcp.tool()
def cart_override_stats(path: str) -> dict:
    """Return the read counters of an override (proof the game read it).

    Parameters:
        path (str): File path inside the ROM.

    Returns:
        dict: ``{"path", "hits", "bytes", "loaded"}`` or ``{"error", "hint"?}``.
    """
    try:
        bridge.refresh_rom()
        result = bridge.cart_override().stats(path)
    except (NdsRomError, ControlError, CartOverrideError) as exc:
        return _override_error(exc)
    return {"path": path, **result}
