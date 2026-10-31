"""MCP tools for the cartridge: filesystem (NitroFS) and overlays."""
import os

from ..application.cart_trace import CartTrace, TraceError
from ..domain.overlays import Overlay
from ..infra.control import ControlError
from ..infra.ndsrom import NdsRomError
from .app import bridge, error, mcp


def _rom_error(exc: Exception) -> dict:
    """Map a ROM/channel failure to the tool error contract."""
    if isinstance(exc, ControlError):
        return error(
            exc, "Verifique se o melonDS está rodando com o canal de controle habilitado."
        )
    return error(exc)


@mcp.tool()
def rom_info() -> dict:
    """Return the ROM loaded in the emulator (the source of truth for cart tools).

    Returns:
        dict: ``{"loaded", "name", "path", "size", "gamecode", "checksum"}`` or
        ``{"error": ...}``.
    """
    try:
        info = bridge.rom_info()
    except (NdsRomError, ControlError) as exc:
        return _rom_error(exc)
    return {
        "loaded": info.loaded,
        "name": info.name,
        "path": info.path,
        "size": info.size,
        "gamecode": info.gamecode,
        "checksum": info.checksum,
    }


@mcp.tool()
def cart_file(offset: int) -> dict:
    """Translate a ROM offset into the corresponding NitroFS file.

    Parameters:
        offset (int): Offset in the ROM (e.g. an address read in the cart trace).

    Returns:
        dict: ``{"file": ...}`` or ``{"error": ...}``.
    """
    try:
        bridge.refresh_rom()
        path = bridge.cartfs().file_for_offset(offset)
    except (NdsRomError, ControlError) as exc:
        return _rom_error(exc)
    if path is None:
        return {"file": None, "error": "offset não pertence a nenhum arquivo NitroFS"}
    return {"file": path}


@mcp.tool()
def cart_list() -> dict:
    """List the ROM filesystem (NitroFS) files.

    Returns:
        dict: ``{"total": N, "files": [{"id", "path"}]}`` or ``{"error": ...}``.
    """
    try:
        bridge.refresh_rom()
        entries = bridge.cartfs().files()
    except (NdsRomError, ControlError) as exc:
        return _rom_error(exc)
    return {
        "total": len(entries),
        "files": [{"id": entry.file_id, "path": entry.path} for entry in entries],
    }


@mcp.tool()
def cart_read(path: str) -> dict:
    """Read a ROM filesystem file and write it to `/out`.

    Parameters:
        path (str): File path inside the ROM (e.g. ``/data/x.sdat``).

    Returns:
        dict: ``{"path", "size"}`` or ``{"error": ...}``.
    """
    try:
        bridge.refresh_rom()
        data = bridge.cartfs().read_file(path)
    except (NdsRomError, ControlError) as exc:
        return _rom_error(exc)
    out_path = bridge.files().write_bytes(os.path.basename(path) or "cart_file.bin", data)
    return {"path": out_path, "size": len(data)}


@mcp.tool()
def cart_read_files(seconds: float = 3.0, batch: int = 256, timeout_ms: int = 100) -> dict:
    """Monitor cartridge reads for a period and aggregate by NitroFS file.

    Starts the trace, collects the reads, stops, and groups by file.

    Parameters:
        seconds (float): Collection duration in seconds.
        batch (int): Items per batch.
        timeout_ms (int): Batch timeout in milliseconds.

    Returns:
        dict: ``{"total": N, "files": {file: count}}`` or ``{"error": ...}``.
    """
    try:
        bridge.refresh_rom()
        channel = bridge.control()
        fs = bridge.cartfs()
    except (NdsRomError, ControlError) as exc:
        return _rom_error(exc)
    try:
        files = CartTrace(channel).by_file(seconds, fs, batch, timeout_ms)
    except TraceError as exc:
        return {"error": str(exc)}
    return {"total": sum(files.values()), "files": files}


def _overlay_dict(overlay: Overlay) -> dict:
    """Serialize an overlay for the tool response."""
    return {
        "core": overlay.core,
        "index": overlay.index,
        "ram_address": overlay.ram_address,
        "ram_size": overlay.ram_size,
        "bss_size": overlay.bss_size,
        "file_id": overlay.file_id,
    }


@mcp.tool()
def overlay_list(core: str | None = None) -> dict:
    """List the ROM overlays (ARM9 and/or ARM7).

    Parameters:
        core (str | None): ``arm9``, ``arm7`` or None for both.

    Returns:
        dict: ``{"arm9": [...], "arm7": [...]}`` (or just the requested core) or ``{"error": ...}``.
    """
    try:
        bridge.refresh_rom()
        overlays = bridge.overlays()
        cores = [core] if core else ["arm9", "arm7"]
        return {name: [_overlay_dict(o) for o in overlays.overlay_list(name)] for name in cores}
    except (NdsRomError, ControlError) as exc:
        return _rom_error(exc)


@mcp.tool()
def overlay_for_address(addr: int, core: str = "arm9") -> dict:
    """Resolve a RAM address to the overlay that contains it.

    Parameters:
        addr (int): RAM address.
        core (str): ``arm9`` or ``arm7``.

    Returns:
        dict: ``{"overlay": {...}, "offset"}`` or ``{"overlay": None}``.
    """
    try:
        bridge.refresh_rom()
        hit = bridge.overlays().overlay_for_address(addr, core)
    except (NdsRomError, ControlError) as exc:
        return _rom_error(exc)
    if hit is None:
        return {"overlay": None}
    return {"overlay": _overlay_dict(hit.overlay), "offset": hit.offset}
