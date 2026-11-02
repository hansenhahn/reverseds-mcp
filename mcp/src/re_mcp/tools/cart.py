"""MCP tools for the cartridge: filesystem (NitroFS) and overlays."""
import os

from ..application.cart_trace import CartTrace, TraceError
from ..domain.cartfs import NdsHeader
from ..domain.overlays import Overlay, OverlayDetails, OverlayHit
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
    """Serialize an overlay hit with its file/code offsets."""
    return {
        **_overlay_dict(hit.overlay),
        "offset": hit.offset_file,
        "offset_file": hit.offset_file,
        "offset_code": hit.offset_code,
    }


def _overlay_details_dict(details: OverlayDetails) -> dict:
    """Serialize an overlay's y9/FAT/compression details."""
    return {
        **_overlay_dict(details.overlay),
        "file_offset": details.file_offset,
        "file_size": details.file_size,
        "compressed": details.compressed,
        "compressed_size": details.compressed_size,
        "code_base": details.code_base,
        "prefix_size": details.prefix_size,
    }


@mcp.tool()
def rom_details(
    overlay: int | None = None, code_base: int | None = None
) -> dict:
    """Return full details of the ROM loaded in the emulator.

    Reads the full header over the control channel and derives the NitroFS file
    count and overlay counts. When the debugger is connected, includes the
    current core, PC and the overlay candidates at the PC; otherwise ``runtime``
    is null.

    Parameters:
        overlay (int | None): Explicit overlay ID for the runtime resolution.
        code_base (int | None): Optional overlay code base (for ``offset_code``).

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
            resolution = bridge.overlay_resolver().resolve(
                pc, core, overlay, code_base
            )
            runtime = {
                "core": core,
                "pc": f"0x{pc:08x}",
                "overlays": [
                    _overlay_hit_dict(hit) for hit in resolution.candidates
                ],
                "overlay": (
                    _overlay_hit_dict(resolution.selected)
                    if resolution.selected
                    else None
                ),
                "ambiguous": resolution.ambiguous,
            }
    except DebugError:
        runtime = None
    except ValueError as exc:
        return error(exc, "code_base deve estar dentro do intervalo da overlay.")

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
        "sinit_start": overlay.sinit_start,
        "sinit_end": overlay.sinit_end,
        "flags": overlay.flags,
        "compressed_size": overlay.compressed_size,
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
def overlay_for_address(
    addr: int,
    core: str = "arm9",
    overlay: int | None = None,
    code_base: int | None = None,
) -> dict:
    """Resolve a RAM address to all overlay candidates.

    Overlays may share a ``ram_address``; the tool returns every candidate and
    flags ambiguity instead of silently picking the first. ``overlay`` selects
    one explicitly; otherwise the active ``overlay_select`` selection is used.

    Parameters:
        addr (int): RAM address.
        core (str): ``arm9`` or ``arm7``.
        overlay (int | None): Explicit overlay ID for the selected hit.
        code_base (int | None): Optional overlay code base (for ``offset_code``).

    Returns:
        dict: Candidates, selected overlay, ambiguity and offsets.
    """
    try:
        bridge.refresh_rom()
        resolution = bridge.overlay_resolver().resolve(
            addr, core, overlay, code_base
        )
    except (NdsRomError, ControlError) as exc:
        return _rom_error(exc)
    except ValueError as exc:
        return error(exc, "code_base deve estar dentro do intervalo da overlay.")
    selected = resolution.selected
    return {
        "found": bool(resolution.candidates),
        "ambiguous": resolution.ambiguous,
        "overlays": [_overlay_hit_dict(hit) for hit in resolution.candidates],
        "overlay": _overlay_hit_dict(selected) if selected else None,
        "offset": selected.offset_file if selected else None,
        "offset_file": selected.offset_file if selected else None,
        "offset_code": selected.offset_code if selected else None,
        "code_base": resolution.code_base,
        "prefix_size": resolution.prefix_size,
    }


@mcp.tool()
def overlay_details(
    index: int, core: str = "arm9", code_base: int | None = None
) -> dict:
    """Return y9/FAT/compression details of an overlay.

    Parameters:
        index (int): Overlay ID.
        core (str): ``arm9`` or ``arm7``.
        code_base (int | None): Optional address where the overlay code starts.

    Returns:
        dict: y9 fields + ``file_offset``/``file_size`` + compression + optional
        ``code_base``/``prefix_size``, or ``{"error", "hint"?}``.
    """
    try:
        bridge.refresh_rom()
        details = bridge.overlay_resolver().details(index, core, code_base)
    except NdsRomError as exc:
        return error(
            exc, "Confira o índice em overlay_list; a ROM precisa ter overlay/FAT."
        )
    except ControlError as exc:
        return _rom_error(exc)
    except ValueError as exc:
        return error(exc, "code_base deve estar dentro do intervalo da overlay.")
    return _overlay_details_dict(details)


@mcp.tool()
def overlay_select(
    index: int | None = None, core: str = "arm9", code_base: int | None = None
) -> dict:
    """Select (or clear) the overlay considered resident for subsequent queries.

    This is MCP session state; it does not prove residency and does not change
    the emulator. Use ``overlay_select(None)`` to clear.

    Parameters:
        index (int | None): Overlay ID, or None to clear.
        core (str): ``arm9`` or ``arm7``.
        code_base (int | None): Optional address where the overlay code starts.

    Returns:
        dict: ``{"core", "overlay", "code_base", "prefix_size"}`` or
        ``{"error", "hint"?}``.
    """
    if index is None:
        bridge.clear_overlay(core)
        return {"core": core, "overlay": None, "code_base": None, "prefix_size": None}
    try:
        bridge.refresh_rom()
        details = bridge.overlay_resolver().select(index, core, code_base)
    except NdsRomError as exc:
        return error(
            exc, "Confira o índice em overlay_list; a ROM precisa ter overlay/FAT."
        )
    except ControlError as exc:
        return _rom_error(exc)
    except ValueError as exc:
        return error(exc, "code_base deve estar dentro do intervalo da overlay.")
    return {
        "core": core,
        "overlay": index,
        "code_base": details.code_base if details else None,
        "prefix_size": details.prefix_size if details else None,
    }
