"""MCP tools for video: `video_state`, `vram_layout` and `read_vram`."""
from ..application.video import VideoReader
from ..domain.io import VramBinding
from ..infra.gdb import DebugError
from .app import bridge, debug_error, mcp, reg_dict


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
        state = VideoReader(bridge.debugger()).state(engine)
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

    The target must be **stopped**. Note: GBATEK marks ``VRAMCNT`` as write-only, but
    melonDS exposes the value on reads, so the layout can be read live.

    Returns:
        dict: ``{"bindings": [...]}`` or ``{"error", "hint"?}``.
    """
    try:
        bindings = VideoReader(bridge.debugger()).vram_layout()
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
        data = VideoReader(bridge.debugger()).read_vram(addr, size)
    except DebugError as exc:
        return debug_error(exc)
    return {"addr": addr, "size": len(data), "hex": data.hex()}
