"""MCP tools for video: `video_state`, `vram_layout`, `read_vram` and `render_layer`."""
from ..application.video import VideoReader
from ..domain.io import VramBinding
from ..infra.gdb import DebugError
from .app import (
    bridge,
    control_call,
    debug_error,
    mcp,
    reg_dict,
    save_framebuffer_pngs,
)


def _binding_dict(binding: VramBinding) -> dict:
    """Serialize a VRAM binding for a tool response."""
    return {
        "bank": binding.bank,
        "mst": binding.mst,
        "offset": binding.offset,
        "target": binding.target,
        "address": f"0x{binding.address:08x}" if binding.address is not None else None,
    }


@mcp.tool()
def video_state(engine: str = "A") -> dict:
    """Read the decoded video state of an engine (with its top/bottom screen).

    The target must be **stopped**.

    Parameters:
        engine (str): ``A`` or ``B``.

    Returns:
        dict: ``{"engine", "screen", "dispcnt", "bgs", "master_bright"}`` or ``{"error", "hint"?}``.
    """
    try:
        state = VideoReader(bridge.debugger(), bridge.io_map()).state(engine)
    except DebugError as exc:
        return debug_error(exc)
    return {
        "engine": state.engine,
        "screen": state.screen,
        "dispcnt": reg_dict(state.dispcnt),
        "bgs": [reg_dict(bg) for bg in state.bgs],
        "master_bright": reg_dict(state.master_bright),
    }


@mcp.tool()
def vram_layout() -> dict:
    """Resolve the current ``VRAMCNT`` into the bank→window layout.

    The target must be **stopped**. Note: ``VRAMCNT`` is write-only on real hardware,
    but melonDS exposes the value on reads, so the layout can be read live.

    Returns:
        dict: ``{"bindings": [...]}`` or ``{"error", "hint"?}``.
    """
    try:
        bindings = VideoReader(bridge.debugger(), bridge.io_map()).vram_layout()
    except DebugError as exc:
        return debug_error(exc)
    return {"bindings": [_binding_dict(b) for b in bindings]}


@mcp.tool()
def read_vram(addr: int, size: int) -> dict:
    """Read VRAM bytes and return them in hexadecimal.

    Parameters:
        addr (int): The VRAM address (e.g. ``0x06000000``).
        size (int): Number of bytes.

    Returns:
        dict: ``{"addr", "size", "hex"}`` or ``{"error", "hint"?}``.
    """
    try:
        data = VideoReader(bridge.debugger(), bridge.io_map()).read_vram(addr, size)
    except DebugError as exc:
        return debug_error(exc)
    return {"addr": addr, "size": len(data), "hex": data.hex()}


@mcp.tool()
def render_layer(
    engine: str = "A", layer: str = "obj", screens: str = "both", format: str = "rgba8"
) -> dict:
    """Render a single video layer of the current frame and save it as PNG.

    Uses the **emulator's own renderer** as an oracle (not a reimplementation), drawing
    only the requested layer (engine ``A``/``B`` x ``bg0``-``bg3``/``obj``/``3d``). It
    does not execute CPU code and does not disturb the displayed frame; the emulator
    keeps running (or stays stopped) as before. Combine with ``emu_step_frame``
    to render a specific frozen frame.

    Parameters:
        engine (str): ``A`` or ``B``.
        layer (str): ``bg0``, ``bg1``, ``bg2``, ``bg3``, ``obj`` or ``3d`` (3D: engine A only).
        screens (str): ``top``, ``bottom`` or ``both``.
        format (str): ``rgba8`` or ``bgra8``.

    Returns:
        dict: ``{"paths": [...]}`` with the saved PNGs, or ``{"error", "hint"?}``.
    """
    result = control_call(
        "video.render_layer",
        {"engine": engine, "layer": layer, "screens": screens, "format": format},
    )
    if "error" in result:
        if "timed out" in str(result["error"]).lower():
            result["hint"] = (
                "O render expirou: a captura de tela exige o renderer de software."
            )
        return result

    return save_framebuffer_pngs(
        result, format=format, prefix=f"layer_{engine}_{layer}"
    )
