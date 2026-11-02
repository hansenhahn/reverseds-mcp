"""MCP tools for video: `video_state`, `vram_layout`, `read_vram` and `render_layer`."""
from PIL import Image, ImageDraw

from ..application.display import DisplayReader
from ..application.video import VideoReader
from ..domain.io import VramBinding
from ..infra.gdb import DebugError
from .app import (
    bridge,
    control_call,
    debug_error,
    error,
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
        "scroll": [
            {"hofs": hofs.raw, "vofs": vofs.raw}
            for hofs, vofs in state.scrolls
        ],
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
    engine: str = "A",
    layer: str = "obj",
    screens: str = "both",
    format: str = "rgba8",
    highlight: list[int] | None = None,
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
        highlight (list[int] | None): Optional ``[x, y]`` screen pixel; draws an 8×8
            rectangle on the BG cell and returns its metadata (BG layers only).

    Returns:
        dict: ``{"paths": [...]}`` (plus ``cell``/``screen`` when highlighting), or
        ``{"error", "hint"?}``.
    """
    cell = None
    state = None
    if highlight is not None:
        if layer not in ("bg0", "bg1", "bg2", "bg3"):
            return error(
                ValueError("highlight só é suportado em bg0..bg3"),
                "Use highlight com uma camada BG text.",
            )
        if len(highlight) != 2:
            return error(ValueError("highlight deve ser [x, y]"), "Use [x, y].")
        x, y = int(highlight[0]), int(highlight[1])
        bg = int(layer[2])
        try:
            debugger = bridge.debugger()
            state = VideoReader(debugger, bridge.io_map()).state(engine)
            screen_cell, cell = DisplayReader(
                debugger, bridge.io_map()
            ).cell_at_screen(engine, bg, x, y)
        except DebugError as exc:
            return debug_error(exc)
        except ValueError as exc:
            return error(
                exc, "Use BG text e coordenadas 0..255/0..191; affine é follow-up."
            )
        if screens == "top" and state.screen != "top":
            return error(
                ValueError("a tela do engine não é top"),
                f"O engine {engine} está na tela {state.screen}; use screens={state.screen}.",
            )
        if screens == "bottom" and state.screen != "bottom":
            return error(
                ValueError("a tela do engine não é bottom"),
                f"O engine {engine} está na tela {state.screen}; use screens={state.screen}.",
            )

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

    saved = save_framebuffer_pngs(
        result, format=format, prefix=f"layer_{engine}_{layer}"
    )
    if cell is None or state is None:
        return saved

    index = 0
    if screens == "both":
        index = 0 if state.screen == "top" else 1
    paths = saved.get("paths", [])
    if index >= len(paths):
        return error(
            ValueError("PNG da tela esperada não foi gerado"),
            "Confira screens e o engine.",
        )
    x0, y0, _, _ = screen_cell.screen_rect
    image = Image.open(paths[index]).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle([x0, y0, x0 + 7, y0 + 7], outline=(255, 0, 0, 255), width=1)
    image.save(paths[index])
    from .re import _cell_dict

    out = {"paths": paths, "screen": state.screen, "cell": _cell_dict(cell)}
    return out
