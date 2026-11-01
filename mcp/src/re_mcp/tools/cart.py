"""MCP tools for the cartridge: filesystem (NitroFS) and overlays."""
import os

from ..application.cart_trace import CartTrace, TraceError
from ..domain.cartfs import NdsHeader
from ..domain.overlays import Overlay, OverlayHit
from ..infra.control import ControlError
from ..infra.gdb import DebugError
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


def _header_dict(header: NdsHeader) -> dict:
    """Serialize the full NDS header."""
    return {
        "title": header.title,
        "gamecode": header.gamecode,
        "makercode": header.makercode,
        "unitcode": header.unitcode,
        "encryption_seed": header.encryption_seed,
        "device_capacity": header.device_capacity,
        "region": header.region,
        "rom_version": header.rom_version,
        "autostart": header.autostart,
        "arm9": {
            "rom_offset": header.arm9_rom_offset,
            "entry": header.arm9_entry,
            "ram_address": header.arm9_ram_address,
            "size": header.arm9_size,
        },
        "arm7": {
            "rom_offset": header.arm7_rom_offset,
            "entry": header.arm7_entry,
            "ram_address": header.arm7_ram_address,
            "size": header.arm7_size,
        },
        "fnt": {"offset": header.fnt_offset, "size": header.fnt_size},
        "fat": {"offset": header.fat_offset, "size": header.fat_size},
        "arm9_overlay_table": {
            "offset": header.arm9_overlay_offset,
            "size": header.arm9_overlay_size,
        },
        "arm7_overlay_table": {
            "offset": header.arm7_overlay_offset,
            "size": header.arm7_overlay_size,
        },
        "icon_offset": header.icon_offset,
        "secure_area_crc": header.secure_area_crc,
        "secure_area_delay": header.secure_area_delay,
        "total_used_size": header.total_used_size,
        "header_size": header.header_size,
        "logo_crc": header.logo_crc,
        "header_crc": header.header_crc,
    }


def _overlay_hit_dict(hit: OverlayHit) -> dict:
    """Serialize an overlay hit with its offset."""
    return {**_overlay_dict(hit.overlay), "offset": hit.offset}


@mcp.tool()
def rom_details() -> dict:
    """Return full details of the ROM loaded in the emulator.

    Reads the full header over the control channel and derives the NitroFS file
    count and overlay counts. When the debugger is connected, includes the
    current core, PC and overlay at the PC; otherwise ``runtime`` is null.

    Returns:
        dict: ``{"loaded", "identity", "header", "derived", "runtime"}`` or
        ``{"error": ...}``.
    """
    try:
        info = bridge.rom_info()
        if not info.loaded:
            return {"loaded": False}
        cartfs = bridge.cartfs()
        overlays = bridge.overlays()
        header = cartfs.header()
        file_count = cartfs.file_count()
        arm9_overlays = len(overlays.overlay_list("arm9"))
        arm7_overlays = len(overlays.overlay_list("arm7"))
    except (NdsRomError, ControlError) as exc:
        return _rom_error(exc)

    runtime = None
    try:
        debugger = bridge.debugger()
        core = debugger.core()
        if core:
            pc = debugger.read_register("pc")
            hit = overlays.overlay_for_address(pc, core)
            runtime = {
                "core": core,
                "pc": f"0x{pc:08x}",
                "overlay": _overlay_hit_dict(hit) if hit else None,
            }
    except DebugError:
        runtime = None

    return {
        "loaded": True,
        "identity": {
            "name": info.name,
            "path": info.path,
            "size": info.size,
            "gamecode": info.gamecode,
            "checksum": info.checksum,
        },
        "header": _header_dict(header),
        "derived": {
            "file_count": file_count,
            "arm9_overlays": arm9_overlays,
            "arm7_overlays": arm7_overlays,
        },
        "runtime": runtime,
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
