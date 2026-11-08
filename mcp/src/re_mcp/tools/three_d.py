"""MCP tools for the 3D engine: state, polygons, textures and the GXFIFO trace.

These read the emulator's own 3D core (read-only). State/polygons/textures come
from a one-shot snapshot taken at VBlank, so they describe the same completed
frame. The GXFIFO trace records the entries enqueued on the writer path (CPU or
DMA), decoded on the client side.
"""
import hashlib
import time

from ..infra.gdb import DebugError
from .app import (
    bridge,
    control_call,
    debug_error,
    error,
    mcp,
    save_framebuffer_pngs,
)

_SNAPSHOT_HINT = (
    "O snapshot do 3D é tirado no VBlank; se o emulador estiver pausado "
    "(debugger parado), retome a execução e tente de novo."
)
_GXFIFO_HINT = (
    "Ligue a trace com gxfifo_trace_start() antes de ler; o melonDS precisa estar "
    "com o canal de controle ativo."
)


def _snapshot_result(result: dict) -> dict:
    if "error" in result and "timeout" in str(result["error"]).lower():
        result.setdefault("hint", _SNAPSHOT_HINT)
    return result


@mcp.tool()
def gpu3d_state() -> dict:
    """Read the decoded 3D engine state of the last completed frame (read-only).

    Includes enable flags, DISP3DCNT/GXStat, FIFO levels, matrix mode, the
    projection/position/vector/texture matrices, viewport, fog and polygon/vertex
    counts. The snapshot is taken at VBlank, so the emulator must be running.

    Returns:
        dict: the decoded 3D state, or ``{"error", "hint"?}``.
    """
    return _snapshot_result(control_call("3d.state"))


@mcp.tool()
def gpu3d_polygons(max_items: int = 512, vertices: bool = True) -> dict:
    """Dump the polygons of the last completed 3D frame (read-only).

    Parameters:
        max_items (int): Maximum polygons to return (1..8192).
        vertices (bool): Include per-vertex screen positions/colors/texcoords.

    Returns:
        dict: ``{"frame", "count", "total", "polygons": [...]}`` or
        ``{"error", "hint"?}``.
    """
    return _snapshot_result(
        control_call("3d.polygons", {"max_items": max_items, "vertices": vertices})
    )


@mcp.tool()
def gpu3d_textures() -> dict:
    """List the textures used by the polygons of the last completed frame.

    Returns:
        dict: ``{"frame", "count", "textures": [...]}`` with
        ``tex_param``/``tex_palette``/``format``/``width``/``height``/``vram_addr``,
        or ``{"error", "hint"?}``.
    """
    return _snapshot_result(control_call("3d.textures"))


@mcp.tool()
def gpu3d_texture_dump(
    index: int | None = None,
    tex_param: int | None = None,
    tex_palette: int | None = None,
) -> dict:
    """Decode one 3D texture to PNG in ``/out``.

    Select either ``index`` (from ``gpu3d_textures``) or an explicit
    ``tex_param``/``tex_palette`` pair. The decoder is the emulator's own.

    Parameters:
        index (int | None): Texture index from ``gpu3d_textures``.
        tex_param (int | None): Explicit texture parameter.
        tex_palette (int | None): Explicit texture palette base.

    Returns:
        dict: ``{"paths": [...], "width", "height"}`` or ``{"error", "hint"?}``.
    """
    params: dict = {}
    if index is not None:
        params["index"] = index
        prefix = f"texture_{index}"
    elif tex_param is not None:
        params["tex_param"] = tex_param
        params["tex_palette"] = tex_palette or 0
        prefix = f"texture_{tex_param:08x}"
    else:
        return {
            "error": "informe index ou tex_param/tex_palette",
            "hint": "Use gpu3d_textures() para listar as texturas do frame.",
        }

    result = control_call("3d.texture", params, timeout=8.0)
    if "error" in result:
        return result

    saved = save_framebuffer_pngs(result, format="rgba8", prefix=prefix)
    if not saved.get("paths"):
        return {
            "error": "textura veio vazia",
            "hint": "Talvez o formato não seja suportado; confira gpu3d_textures().",
        }
    binary = result.get("binary", {})
    saved["width"] = binary.get("width")
    saved["height"] = binary.get("height")
    return saved


@mcp.tool()
def gxfifo_trace_start(max_items: int = 65536) -> dict:
    """Start recording GXFIFO command entries (writer path).

    Each entry has ``cmd``, ``param``, ``pc``, ``frame`` and ``fifo`` (queue depth
    before the enqueue). For DMA-fed FIFO the ``pc`` is the CPU PC at the write,
    not necessarily the DMA programmer — pair with ``dma_trace`` when that matters.

    Parameters:
        max_items (int): Ring capacity (oldest entries dropped on overflow).

    Returns:
        dict: ``{"ok", "max_items"}`` or ``{"error", "hint"?}``.
    """
    return control_call("3d.gxfifo.start", {"max_items": max_items})


@mcp.tool()
def gxfifo_trace_read(seconds: float = 0.0, decode: str = "raw") -> dict:
    """Drain the buffered GXFIFO entries (optionally after waiting ``seconds``).

    Parameters:
        seconds (float): Wait this long before draining (e.g. to collect frames).
        decode (str): ``raw`` (default) or ``typed`` (adds semantic fields per
            command: vertex x/y/z, texcoord u/v, matrix mode/elements, primitive).

    Returns:
        dict: ``{"count", "dropped", "commands": [...]}`` or ``{"error", "hint"?}``.
    """
    if seconds > 0:
        time.sleep(seconds)
    result = control_call("3d.gxfifo.read")
    if "error" in result:
        result.setdefault("hint", _GXFIFO_HINT)
        return result
    if decode == "typed":
        for command in result.get("commands", []):
            command["typed"] = _decode_gx_command(command)
    return result


@mcp.tool()
def gxfifo_trace_stop() -> dict:
    """Stop recording GXFIFO entries (already-collected entries stay readable).

    Returns:
        dict: ``{"ok": true}`` or ``{"error", "hint"?}``.
    """
    return control_call("3d.gxfifo.stop")


def _s16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def _s10(value: int) -> int:
    value &= 0x3FF
    return value - 0x400 if value & 0x200 else value


def _decode_gx_command(command: dict) -> dict | None:
    """Decode one GXFIFO command's params into semantic fields (best effort)."""
    cmd = command.get("cmd")
    params = command.get("params", [])
    if not params and cmd not in (0x41, 0x00):
        return None
    p = params[0] if params else 0
    if cmd == 0x23 and len(params) >= 2:
        return {"x": _s16(p), "y": _s16(p >> 16), "z": _s16(params[1])}
    if cmd == 0x24:
        return {"x": _s10(p), "y": _s10(p >> 10), "z": _s10(p >> 20)}
    if cmd == 0x25:
        return {"x": _s16(p), "y": _s16(p >> 16)}
    if cmd == 0x26:
        return {"x": _s16(p), "z": _s16(p >> 16)}
    if cmd == 0x27:
        return {"y": _s16(p), "z": _s16(p >> 16)}
    if cmd == 0x28:
        return {"dx": _s10(p), "dy": _s10(p >> 10), "dz": _s10(p >> 20)}
    if cmd == 0x22:
        return {"u": _s16(p), "v": _s16(p >> 16)}
    if cmd == 0x40:
        prim = p & 0x3
        names = ["triangles", "quads", "triangle_strip", "quad_strip"]
        return {"primitive": prim, "primitive_name": names[prim]}
    if cmd == 0x10:
        return {"mode": p & 0x3}
    if cmd in (0x1B, 0x1C):
        return {"x": _s16(p), "y": _s16(p >> 16), "z": _s16(params[1]) if len(params) > 1 else None}
    if cmd == 0x20:
        return {"color": p}
    if cmd == 0x29:
        return {"attr": p}
    if cmd == 0x2A:
        return {"teximage_param": p}
    return None


def _find_pattern(pattern: bytes, ram_start: int, ram_size: int, max_hits: int) -> list[int]:
    """Search ``pattern`` in RAM in chunks (with overlap), returning addresses."""
    debugger = bridge.debugger()
    step = 1 << 20
    overlap = max(0, len(pattern) - 1)
    hits: list[int] = []
    seen: set[int] = set()
    offset = 0

    while offset < ram_size and len(hits) < max_hits:
        want = min(step + overlap, ram_size - offset)
        data = debugger.read_memory(ram_start + offset, want)
        if not data:
            break
        base = ram_start + offset
        pos = 0
        while True:
            idx = data.find(pattern, pos)
            if idx < 0:
                break
            addr = base + idx
            if addr not in seen:
                seen.add(addr)
                hits.append(addr)
                if len(hits) >= max_hits:
                    break
            pos = idx + 1
        if want < step + overlap:
            break
        offset += step

    return hits


@mcp.tool()
def gpu3d_texture_source(
    index: int | None = None,
    tex_param: int | None = None,
    tex_palette: int | None = None,
    ram_start: int = 0x02000000,
    ram_size: int = 4 * 1024 * 1024,
    max_hits: int = 16,
    dump_source: bool = False,
) -> dict:
    """Find the RAM buffer(s) holding a 3D texture's raw bytes (its origin).

    Reads the texture's raw bytes from the emulator's texture VRAM and searches
    RAM for an identical byte pattern. The hit(s) are candidate source buffers;
    set a watchpoint there to find the loader in code.

    Parameters:
        index (int | None): Texture index from ``gpu3d_textures``.
        tex_param (int | None): Explicit texture parameter (alternative to index).
        tex_palette (int | None): Explicit palette base for ``tex_param``.
        ram_start (int): RAM search start (default main RAM).
        ram_size (int): RAM search size.
        max_hits (int): Maximum candidates.
        dump_source (bool): Save the candidate buffer(s) as ``.bin`` in ``/out``.

    Returns:
        dict: texture info + ``candidates``/``count``/``unknown`` (+ ``paths``), or
        ``{"error", "hint"?}``.
    """
    info: dict = {}
    if index is not None:
        textures = _snapshot_result(control_call("3d.textures"))
        if "error" in textures:
            return textures
        items = textures.get("textures", [])
        if index < 0 or index >= len(items):
            return {"error": f"texture index out of range (0..{len(items) - 1})"}
        info = items[index]
        tex_param = info["tex_param"]
        tex_palette = info["tex_palette"]
    elif tex_param is not None:
        tex_palette = tex_palette or 0
    else:
        return {
            "error": "informe index ou tex_param/tex_palette",
            "hint": "Use gpu3d_textures() para listar as texturas do frame.",
        }

    raw = control_call(
        "3d.texture_raw",
        {"tex_param": tex_param, "tex_palette": tex_palette or 0},
        timeout=8.0,
    )
    if "error" in raw:
        return raw

    pattern = raw.get("binary", {}).get("data", b"")
    if not pattern:
        return {"error": "textura crua veio vazia"}

    try:
        hits = _find_pattern(pattern, ram_start, ram_size, max_hits)
    except DebugError as exc:
        return debug_error(exc)

    paths: list[str] = []
    if dump_source:
        debugger = bridge.debugger()
        for addr in hits:
            try:
                data = debugger.read_memory(addr, len(pattern))
            except DebugError as exc:
                return debug_error(exc)
            name = f"texture_src_{tex_param:08x}_{addr:08x}.bin"
            paths.append(bridge.files().write_bytes(name, data))

    return {
        "tex_param": tex_param,
        "tex_palette": tex_palette,
        "format_id": raw.get("format_id"),
        "width": raw.get("binary", {}).get("width"),
        "height": raw.get("binary", {}).get("height"),
        "size": len(pattern),
        "digest": hashlib.sha256(pattern).hexdigest(),
        "count": len(hits),
        "candidates": [f"0x{addr:08x}" for addr in hits],
        "unknown": not hits,
        "paths": paths,
    }


@mcp.tool()
def gxfifo_source(
    max_age_frames: int = 0,
    max_hits: int = 8,
    dump_source: bool = False,
) -> dict:
    """Find the buffer (display list) that feeds the GXFIFO, from the write history.

    Requires the origin history to have been armed (``origin.start``) while the
    display list was uploaded.

    Parameters:
        max_age_frames (int): Only hits within this many frames (0 = any).
        max_hits (int): Maximum hits.
        dump_source (bool): Save the ``src`` buffer(s) as ``.bin`` in ``/out``.

    Returns:
        dict: ``{"count", "unknown", "hits": [...]}`` (+ ``paths``), or
        ``{"error", "hint"?}``.
    """
    result = control_call(
        "gxfifo.origin",
        {"max_age_frames": max_age_frames, "max_hits": max_hits},
    )
    if "error" in result:
        result.setdefault(
            "hint",
            "Arme o histórico com origin.start() antes de o jogo carregar a display list.",
        )
        return result

    paths: list[str] = []
    if dump_source:
        debugger = bridge.debugger()
        for hit in result.get("hits", []):
            try:
                data = debugger.read_memory(hit["src"], hit["len"])
            except DebugError as exc:
                return debug_error(exc)
            name = f"gxfifo_src_{hit['src']:08x}.bin"
            paths.append(bridge.files().write_bytes(name, data))
    result["paths"] = paths
    return result


@mcp.tool()
def find_bytes_in_ram(
    hex_data: str | None = None,
    from_addr: int | None = None,
    size: int = 0,
    ram_start: int = 0x02000000,
    ram_size: int = 4 * 1024 * 1024,
    max_hits: int = 16,
) -> dict:
    """Search RAM for a byte pattern (or for the bytes of a memory region).

    Parameters:
        hex_data (str | None): Pattern in hex (e.g. ``"deadbeef"``).
        from_addr (int | None): Alternatively, take the pattern from this address.
        size (int): Pattern size when using ``from_addr``.
        ram_start (int): RAM search start.
        ram_size (int): RAM search size.
        max_hits (int): Maximum hits.

    Returns:
        dict: ``{"count", "hits": ["0x..."]}`` or ``{"error", "hint"?}``.
    """
    if hex_data is not None:
        cleaned = hex_data.replace("0x", "").replace(" ", "").replace("\n", "")
        try:
            pattern = bytes.fromhex(cleaned)
        except ValueError:
            return {"error": "hex_data inválido"}
    elif from_addr is not None:
        if size <= 0:
            return {"error": "size obrigatório quando usa from_addr"}
        try:
            pattern = bridge.debugger().read_memory(from_addr, size)
        except DebugError as exc:
            return debug_error(exc)
    else:
        return {"error": "informe hex_data ou from_addr/size"}

    if not pattern:
        return {"error": "padrão vazio"}
    if ram_size < len(pattern):
        return {"error": "ram_size menor que o padrão"}
    if ram_size > 16 * 1024 * 1024:
        ram_size = 16 * 1024 * 1024

    try:
        hits = _find_pattern(pattern, ram_start, ram_size, max_hits)
    except DebugError as exc:
        return debug_error(exc)

    return {
        "count": len(hits),
        "hits": [f"0x{addr:08x}" for addr in hits],
        "ram_start": f"0x{ram_start:08x}",
        "ram_size": ram_size,
        "pattern_size": len(pattern),
    }


@mcp.tool()
def origin_start(max_items: int = 65536) -> dict:
    """Arm the VRAM write-origin history (DMA) before loading a scene/asset.

    Parameters:
        max_items (int): Ring capacity (oldest entries dropped on overflow).

    Returns:
        dict: ``{"ok", "max_items"}`` or ``{"error", "hint"?}``.
    """
    return control_call("origin.start", {"max_items": max_items})


@mcp.tool()
def origin_stop() -> dict:
    """Stop the origin history (collected entries stay queryable).

    Returns:
        dict: ``{"ok": true}`` or ``{"error", "hint"?}``.
    """
    return control_call("origin.stop")


@mcp.tool()
def origin_query(
    addr: int,
    length: int = 1,
    max_age_frames: int = 0,
    max_hits: int = 16,
) -> dict:
    """Query the origin history for writes overlapping a VRAM range.

    Parameters:
        addr (int): Start of the VRAM range.
        length (int): Range length in bytes.
        max_age_frames (int): Only hits within this many frames (0 = any).
        max_hits (int): Maximum hits (newest first).

    Returns:
        dict: ``{"count", "unknown", "hits": [...]}`` with hex addresses, or
        ``{"error", "hint"?}``.
    """
    result = control_call(
        "origin.query",
        {"addr": addr, "len": length, "max_age_frames": max_age_frames, "max_hits": max_hits},
    )
    if "error" in result:
        result.setdefault("hint", "Arme o histórico com origin_start() antes do upload.")
        return result
    for hit in result.get("hits", []):
        for key in ("src", "dst_lo", "dst_hi", "pc"):
            if key in hit:
                hit[key] = f"0x{hit[key]:08x}"
    return result
