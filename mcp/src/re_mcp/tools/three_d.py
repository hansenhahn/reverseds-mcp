"""MCP tools for the 3D engine: state, polygons, textures and the GXFIFO trace.

These read the emulator's own 3D core (read-only). State/polygons/textures come
from a one-shot snapshot taken at VBlank, so they describe the same completed
frame. The GXFIFO trace records the entries enqueued on the writer path (CPU or
DMA), decoded on the client side.
"""
import time

from .app import control_call, mcp, save_framebuffer_pngs

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
def gxfifo_trace_read(seconds: float = 0.0) -> dict:
    """Drain the buffered GXFIFO entries (optionally after waiting ``seconds``).

    Parameters:
        seconds (float): Wait this long before draining (e.g. to collect frames).

    Returns:
        dict: ``{"count", "dropped", "commands": [...]}`` or ``{"error", "hint"?}``.
    """
    if seconds > 0:
        time.sleep(seconds)
    result = control_call("3d.gxfifo.read")
    if "error" in result:
        result.setdefault("hint", _GXFIFO_HINT)
    return result


@mcp.tool()
def gxfifo_trace_stop() -> dict:
    """Stop recording GXFIFO entries (already-collected entries stay readable).

    Returns:
        dict: ``{"ok": true}`` or ``{"error", "hint"?}``.
    """
    return control_call("3d.gxfifo.stop")
