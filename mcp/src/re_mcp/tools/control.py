"""MCP tools for the control channel: ping, input, screen, savestate, run and trace."""
from ..application.cart_trace import CartTrace
from ..application.dma_trace import DmaTrace
from ..application.input import InputMacros
from ..domain.input import InputStep, TouchPoint
from ..domain.io import DmaTransfer
from ..infra.control import ControlError
from ..infra.gdb import DebugError
from .app import bridge, control_call, error, mcp, save_framebuffer_pngs

_CONTROL_HINT = "Verifique se o melonDS está rodando com o canal de controle habilitado."


@mcp.tool()
def ping() -> dict:
    """Check the connection to the melonDS control channel.

    Returns:
        dict: ``{"pong": true}`` when the emulator responds, or ``{"error": ...}``.
    """
    return control_call("ping")


@mcp.tool()
def health_check() -> dict:
    """Check the control channel and the debugger, with diagnostic hints.

    Creates or tears down no connections: uses the current channel and, if the debugger
    is connected, does a test read of the PC.

    Returns:
        dict: ``{"control": ..., "debug": ...}`` with ``error``/``hint`` per backend.
    """
    out: dict = {}
    try:
        out["control"] = bridge.control().call("ping")
    except ControlError as exc:
        out["control"] = error(exc, "O melonDS está rodando com o canal de controle?")
    debugger = bridge.debugger()
    if debugger.is_running():
        out["debug"] = {"ok": True, "running": True}
    else:
        try:
            pc = debugger.read_register("pc")
            out["debug"] = {"ok": True, "pc": f"0x{pc:08x}"}
        except DebugError as exc:
            out["debug"] = error(
                exc, "Chame debug_connect() (ou reinicie o melonDS se o stub caiu)."
            )
    return out


@mcp.tool()
def input_key(mask: int) -> dict:
    """Set the pressed keys (active-low mask: 1=released, 0=pressed).

    Parameters:
        mask (int): Mask (0xFFF = none; e.g. 0xFF7 = Start).

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    return control_call("input.key", {"mask": mask})


@mcp.tool()
def input_touch(x: int, y: int) -> dict:
    """Press the touch screen at (x, y).

    Parameters:
        x (int): X coordinate.
        y (int): Y coordinate.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    return control_call("input.touch", {"x": x, "y": y})


@mcp.tool()
def input_release() -> dict:
    """Release all keys and the touch screen.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    return control_call("input.release")


@mcp.tool()
def input_tap(mask: int, ms: int = 100) -> dict:
    """Press the mask key(s) for ``ms`` and release (input macro).

    Parameters:
        mask (int): Active-low mask (e.g. ``0xFF7`` = Start).
        ms (int): Tap duration in milliseconds.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    try:
        channel = bridge.control()
    except ControlError as exc:
        return error(exc, _CONTROL_HINT)
    try:
        InputMacros(channel).tap(mask, ms)
        return {"ok": True}
    except ControlError as exc:
        return error(exc, _CONTROL_HINT)


@mcp.tool()
def input_touch_tap(x: int, y: int, ms: int = 100) -> dict:
    """Touch ``(x, y)`` for ``ms`` and release (input macro).

    The touch screen is the **bottom screen** (engine B); coordinates are ``0<=x<256``,
    ``0<=y<192``. Use this for touch-only games (e.g. Hotel Dusk).

    Parameters:
        x (int): X coordinate.
        y (int): Y coordinate.
        ms (int): Touch duration in milliseconds.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    try:
        channel = bridge.control()
    except ControlError as exc:
        return error(exc, _CONTROL_HINT)
    try:
        InputMacros(channel).touch_tap(TouchPoint(x, y), ms)
        return {"ok": True}
    except (ControlError, ValueError) as exc:
        return error(exc, _CONTROL_HINT)


@mcp.tool()
def input_sequence(steps: list[dict]) -> dict:
    """Run a sequence of ``{mask|touch, ms, after_ms}`` steps (input macro).

    Each step holds its input — a button ``mask`` or a ``touch`` at ``(x, y)`` (bottom
    screen, ``0<=x<256``, ``0<=y<192``) — for ``ms``, releases, then waits ``after_ms``.
    A step with neither just waits. The input is released at the end (even on error).

    Parameters:
        steps (list[dict]): Ordered list of steps; each ``{mask|touch, ms, after_ms}``.

    Returns:
        dict: ``{"ok": true, "steps": N}`` or ``{"error": ...}``.
    """
    try:
        channel = bridge.control()
    except ControlError as exc:
        return error(exc, _CONTROL_HINT)
    try:
        parsed = [
            InputStep(
                ms=int(step.get("ms", 100)),
                after_ms=int(step.get("after_ms", 0)),
                mask=(int(step["mask"]) if step.get("mask") is not None else None),
                touch=(
                    TouchPoint(int(step["touch"][0]), int(step["touch"][1]))
                    if step.get("touch") is not None
                    else None
                ),
            )
            for step in steps
        ]
        InputMacros(channel).run(parsed)
        return {"ok": True, "steps": len(parsed)}
    except (ControlError, ValueError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def input_merge(enabled: bool = True) -> dict:
    """Enable/disable merging the agent's input with the host's.

    Parameters:
        enabled (bool): True merges (human + agent); False leaves the agent alone.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    return control_call("input.merge", {"enabled": enabled})


@mcp.tool()
def screen_capture(screens: str = "both", format: str = "rgba8") -> dict:
    """Capture the screen(s) on demand and save them as PNG.

    Parameters:
        screens (str): ``top``, ``bottom`` or ``both``.
        format (str): ``rgba8`` or ``bgra8``.

    Returns:
        dict: ``{"paths": [...]}`` with the saved PNGs, or ``{"error": ...}``.
    """
    result = control_call("screen.capture", {"screens": screens, "format": format})
    if "error" in result:
        if "timed out" in str(result["error"]).lower():
            result["hint"] = (
                "A captura expirou: a CPU pode estar parada (use debug_resume() ou "
                "debug_disconnect()) ou o renderer não é software."
            )
        return result

    return save_framebuffer_pngs(result, format=format, prefix="capture")


@mcp.tool()
def savestate_save(slot: int = 0) -> dict:
    """Save the emulation state to a slot.

    Parameters:
        slot (int): Slot identifier.

    Returns:
        dict: ``{"ok": true, "path": ...}`` or ``{"error": ...}``.
    """
    return control_call("savestate.save", {"slot": slot})


@mcp.tool()
def savestate_load(slot: int = 0) -> dict:
    """Load the emulation state from a slot.

    Parameters:
        slot (int): Slot identifier.

    Returns:
        dict: ``{"ok": true, "path": ...}`` or ``{"error": ...}``.
    """
    return control_call("savestate.load", {"slot": slot})


@mcp.tool()
def emu_pause() -> dict:
    """Pause execution.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    return control_call("emu.pause")


@mcp.tool()
def emu_resume() -> dict:
    """Resume execution.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    return control_call("emu.resume")


@mcp.tool()
def emu_step_frame(n: int = 1) -> dict:
    """Advance exactly ``n`` frames and stop (deterministic frame step).

    Blocks until the ``n`` frames have been emulated, then leaves the emulator
    paused with the framebuffer composed (so a capture right after reflects the
    frozen frame). Resume with ``emu_resume``. Requires the emulator running.

    Parameters:
        n (int): Number of frames to advance (>= 1).

    Returns:
        dict: ``{"ok": true, "frames": n}`` or ``{"error": ...}``.
    """
    return control_call("emu.step_frame", {"n": n})


@mcp.tool()
def cart_trace_start(batch: int = 256, timeout_ms: int = 100, max_items: int = 65536) -> dict:
    """Start the cartridge read trace (overwrites any previous one).

    Parameters:
        batch (int): Items per batch.
        timeout_ms (int): Batch timeout in milliseconds.
        max_items (int): Ring capacity; the oldest reads are dropped past it.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    return control_call(
        "cart.trace.start",
        {"batch": batch, "timeout_ms": timeout_ms, "max_items": max_items},
    )


@mcp.tool()
def cart_trace_read(seconds: float = 2.0) -> dict:
    """Collect the cartridge reads for a period (``event.cart`` batches).

    Parameters:
        seconds (float): Collection duration in seconds.

    Returns:
        dict: ``{"count": N, "reads": [...]}`` or ``{"error": ...}``.
    """
    try:
        channel = bridge.control()
    except ControlError as exc:
        return error(exc, _CONTROL_HINT)
    reads = CartTrace(channel).collect(seconds)
    return {"count": len(reads), "reads": reads}


@mcp.tool()
def cart_trace_stop() -> dict:
    """Stop the cartridge read trace.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    return control_call("cart.trace.stop")


def _dma_dict(transfer: DmaTransfer) -> dict:
    """Serialize a decoded DMA transfer for a tool response.

    Parameters:
        transfer (DmaTransfer): The decoded transfer.

    Returns:
        dict: The serialized transfer (de -> para, length in bytes, decoded control).
    """
    return {
        "channel": transfer.channel,
        "source": {
            "address": f"0x{transfer.source.address:08x}",
            "control": transfer.source.control,
        },
        "destination": {
            "address": f"0x{transfer.destination.address:08x}",
            "control": transfer.destination.control,
        },
        "length": transfer.length,
        "control": {
            field.name: field.meaning if field.meaning is not None else field.value
            for field in transfer.control.fields
        },
        "pc": f"0x{transfer.pc:08x}",
    }


@mcp.tool()
def dma_trace_start(batch: int = 256, timeout_ms: int = 100, max_items: int = 65536) -> dict:
    """Start the DMA transfer trace (overwrites any previous one).

    Each transfer is delivered decoded (de -> para, length in bytes, and the ``DMAxCNT``
    fields). Collect with ``dma_trace_read``.

    Parameters:
        batch (int): Transfers per batch.
        timeout_ms (int): Batch timeout in milliseconds.
        max_items (int): Ring capacity; the oldest transfers are dropped past it.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    return control_call(
        "dma.trace.start",
        {"batch": batch, "timeout_ms": timeout_ms, "max_items": max_items},
    )


@mcp.tool()
def dma_trace_read(seconds: float = 2.0) -> dict:
    """Collect the DMA transfers for a period (``event.dma`` batches), decoded.

    Parameters:
        seconds (float): Collection duration in seconds.

    Returns:
        dict: ``{"count": N, "transfers": [...]}`` or ``{"error": ...}``.
    """
    try:
        channel = bridge.control()
    except ControlError as exc:
        return error(exc, _CONTROL_HINT)
    transfers = DmaTrace(channel).collect(seconds)
    return {"count": len(transfers), "transfers": [_dma_dict(t) for t in transfers]}


@mcp.tool()
def dma_trace_stop() -> dict:
    """Stop the DMA transfer trace.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    return control_call("dma.trace.stop")
