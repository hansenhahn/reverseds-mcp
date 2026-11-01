"""MCP tools for debugging (gdb): memory, registers, breakpoints and execution."""
import json
import re

from ..application.backtrace import Backtrace
from ..application.watchpoints import Watchpoints
from ..domain.debug import Breakpoint
from ..domain.disasm import Disassembler
from ..infra.gdb import DebugError
from .app import bridge, control_call, debug_error, error, mcp


def _breakpoint_dict(breakpoint: Breakpoint) -> dict:
    """Serialize a breakpoint/watchpoint for a tool response."""
    return {
        "number": breakpoint.number,
        "kind": breakpoint.kind,
        "address": (
            f"0x{breakpoint.address:08x}" if breakpoint.address is not None else None
        ),
        "condition": breakpoint.condition,
        "enabled": breakpoint.enabled,
        "hardware": breakpoint.hardware,
    }


@mcp.tool()
def debug_connect(core: str = "arm9") -> dict:
    """Connect the debug backend (gdb) to the chosen core.

    Does a test read of the PC after connecting; if the stub does not respond,
    disconnects and reports an error with a hint.

    Parameters:
        core (str): ``arm9`` or ``arm7``.

    Returns:
        dict: ``{"ok": true, "core": ..., "pc": ...}`` or ``{"error", "hint"?}``.
    """
    try:
        backend = bridge.debugger()
        backend.connect(core)
    except DebugError as exc:
        return debug_error(exc)
    try:
        pc = backend.read_register("pc")
    except DebugError:
        # The stub is only serviced while the CPU runs; if the emulator is paused
        # (emu_pause) it will not answer. Nudge it (a short resume -- the gdb attach
        # halts it again) and retry the read once.
        try:
            control_call("emu.resume")
            pc = backend.read_register("pc")
        except DebugError as exc:
            try:
                backend.disconnect()
            except DebugError:
                pass
            return error(
                exc,
                "O stub GDB pode estar travado; reinicie o melonDS (nds-control.sh / nds-debug.sh).",
            )
    return {"ok": True, "core": core, "pc": f"0x{pc:08x}"}


@mcp.tool()
def debug_read_register(name: str = "pc") -> dict:
    """Read a register of the connected core (e.g. ``pc``).

    Parameters:
        name (str): Register name.

    Returns:
        dict: ``{"name": ..., "value": ...}`` or ``{"error": ...}``.
    """
    try:
        value = bridge.debugger().read_register(name)
        return {"name": name, "value": value, "value_hex": f"0x{value:08x}"}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_write_register(name: str, value: int) -> dict:
    """Write a value to a register.

    Parameters:
        name (str): Register name (e.g. ``pc``).
        value (int): Value to write.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    try:
        bridge.debugger().write_register(name, value)
        return {"ok": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def mem_read(addr: int, size: int) -> dict:
    """Read emulated memory and return the bytes in hexadecimal.

    Parameters:
        addr (int): Start address.
        size (int): Number of bytes.

    Returns:
        dict: ``{"addr": ..., "size": ..., "hex": ...}`` or ``{"error": ...}``.
    """
    try:
        data = bridge.debugger().read_memory(addr, size)
        return {"addr": addr, "size": len(data), "hex": data.hex()}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def mem_write(addr: int, hex_data: str) -> dict:
    """Write bytes (hex) to emulated memory starting at an address.

    Parameters:
        addr (int): Start address.
        hex_data (str): Bytes in hex (e.g. ``deadbeef``).

    Returns:
        dict: ``{"ok": true, "addr": "0x...", "size": N}`` or ``{"error": ...}``.
    """
    try:
        data = bytes.fromhex(hex_data)
        bridge.debugger().write_memory(addr, data)
    except (DebugError, ValueError) as exc:
        return {"error": str(exc)}
    return {"ok": True, "addr": f"0x{addr:08x}", "size": len(data)}


@mcp.tool()
def mem_dump_file(addr: int, size: int, name: str | None = None) -> dict:
    """Read memory and write a ``.bin`` (plus a ``.json``) in the output directory.

    Avoids moving huge hex through the MCP: the file goes to ``RE_MCP_OUT_DIR``
    (mounted on the host, e.g. ``/out``).

    Parameters:
        addr (int): Start address.
        size (int): Number of bytes.
        name (str | None): File name (default ``dump_<addr>_<size>.bin``).

    Returns:
        dict: ``{"path": ..., "addr": ..., "size": ...}`` or ``{"error": ...}``.
    """
    try:
        data = bridge.debugger().read_memory(addr, size)
    except DebugError as exc:
        return debug_error(exc)
    filename = (name if name else f"dump_{addr:08x}_{size:x}.bin")
    if not filename.endswith(".bin"):
        filename += ".bin"
    path = bridge.files().write_bytes(filename, data)
    meta = {"path": path, "addr": addr, "size": len(data)}
    bridge.files().write_text(filename + ".json", json.dumps(meta))
    return meta


@mcp.tool()
def disassemble(addr: int, count: int = 16, mode: str = "arm") -> dict:
    """Disassemble ``count`` instructions starting at ``addr`` (ARM or Thumb).

    Reads memory through the debug backend — the target must be **stopped**.

    Parameters:
        addr (int): Start address.
        count (int): Number of instructions (1..256).
        mode (str): ``arm`` or ``thumb``.

    Returns:
        dict: ``{"addr", "mode", "instructions": [...]}`` or ``{"error": ...}``.
    """
    count = max(1, min(count, 256))
    try:
        data = bridge.debugger().read_memory(addr, count * 4)
    except DebugError as exc:
        return debug_error(exc)
    try:
        instructions = Disassembler().disassemble(data, addr, mode, count)
    except ValueError as exc:
        return {"error": str(exc)}
    symbols = bridge.symbols()
    annotated = []
    for item in instructions:
        symbol = symbols.resolve(item.address)
        target_symbol = None
        if item.mnemonic.startswith("b") and not item.mnemonic.startswith(
            ("bic", "bfi", "bfc", "bkpt")
        ):
            match = re.search(r"0x[0-9a-fA-F]+", item.op_str)
            if match is not None:
                target = symbols.resolve(int(match.group(0), 16))
                target_symbol = target.name if target else None
        annotated.append(
            {
                "address": f"0x{item.address:08x}",
                "size": item.size,
                "bytes": item.bytes_hex,
                "mnemonic": item.mnemonic,
                "op_str": item.op_str,
                "symbol": symbol.name if symbol else None,
                "target_symbol": target_symbol,
            }
        )
    return {"addr": addr, "mode": mode, "instructions": annotated}


@mcp.tool()
def set_breakpoint(
    addr: int,
    condition: str | None = None,
    commands: list[str] | None = None,
) -> dict:
    """Create a code breakpoint at an address, optionally conditional with actions.

    Parameters:
        addr (int): Address.
        condition (str | None): Optional gdb expression; gdb only stops when true.
        commands (list[str] | None): Optional gdb commands run on the hit (one per
            line). Auto-patch example: ``["silent",
            "set {unsigned int}0x062003F0 = 0x...", "continue"]``.

    Returns:
        dict: ``{"number", "addr", "condition", "commands"}`` or ``{"error", "hint"?}``.
    """
    try:
        number = bridge.debugger().set_breakpoint(addr, condition, commands)
    except DebugError as exc:
        return debug_error(exc)
    return {
        "number": number,
        "addr": f"0x{addr:08x}",
        "condition": condition,
        "commands": list(commands or []),
    }


@mcp.tool()
def set_watchpoint(addr: int, kind: str = "write", condition: str | None = None) -> dict:
    """Create a hardware watchpoint (``write``/``read``/``access``).

    Parameters:
        addr (int): Watched address.
        kind (str): Access kind.
        condition (str | None): Optional gdb expression; gdb only stops when it is
            true (filters by value). E.g.
            ``*(unsigned short*)0x0600F448 != 0``.

    Returns:
        dict: ``{"number": N}`` or ``{"error": ...}``.
    """
    try:
        return {"number": bridge.debugger().set_watchpoint(addr, kind, condition)}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def remove_breakpoint(number: int) -> dict:
    """Remove a breakpoint/watchpoint by number.

    Parameters:
        number (int): The number.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    try:
        bridge.debugger().remove(number)
        return {"ok": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_continue(timeout: float = 30.0) -> dict:
    """Resume execution and wait for the stop (breakpoint/watchpoint).

    Parameters:
        timeout (float): Maximum wait time in seconds.

    Returns:
        dict: ``{"stopped": bool}`` or ``{"error": ...}``.
    """
    try:
        stopped = bridge.debugger().continue_(timeout)
        return {"stopped": stopped}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_resume() -> dict:
    """Resume execution in the background (NON-blocking).

    Unlike ``debug_continue`` (runs until it stops), this leaves the target running
    with gdb still attached, so the agent can inject input (control channel) and then
    use ``debug_wait`` to pick up the stop.

    Returns:
        dict: ``{"ok": true, "running": true}`` or ``{"error": ...}``.
    """
    try:
        bridge.debugger().resume()
        return {"ok": True, "running": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_wait(timeout: float = 30.0) -> dict:
    """Wait for the background ``continue`` to stop (breakpoint/watchpoint).

    Parameters:
        timeout (float): Maximum wait time in seconds.

    Returns:
        dict: ``{"stopped": bool, "running": bool}`` or ``{"error": ...}``.
    """
    try:
        stopped = bridge.debugger().wait_stop(timeout)
        return {"stopped": stopped, "running": not stopped}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_step() -> dict:
    """Execute one instruction.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    try:
        bridge.debugger().step()
        return {"ok": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_interrupt() -> dict:
    """Interrupt execution.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    try:
        bridge.debugger().interrupt()
        return {"ok": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_disconnect() -> dict:
    """Disconnect the debug backend — the emulator runs again.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    try:
        bridge.debugger().disconnect()
        return {"ok": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_backtrace() -> dict:
    """Return the call stack of the connected core (innermost frame first).

    Requires the target to be stopped.

    Returns:
        dict: ``{"frames": [{"index", "pc", "function", "source"}]}`` or
        ``{"error", "hint"?}``.
    """
    try:
        frames = Backtrace(bridge.debugger()).frames()
    except DebugError as exc:
        return debug_error(exc)
    symbols = bridge.symbols()
    annotated = []
    for frame in frames:
        symbol = symbols.resolve(frame.pc)
        annotated.append(
            {
                "index": frame.index,
                "pc": f"0x{frame.pc:08x}",
                "function": frame.function or (symbol.name if symbol else None),
                "source": frame.source,
                "symbol": symbol.name if symbol else None,
            }
        )
    return {"frames": annotated}


@mcp.tool()
def list_breakpoints() -> dict:
    """List the active breakpoints and watchpoints.

    Returns:
        dict: ``{"breakpoints": [{"number","kind","address","condition","enabled"}]}``
        or ``{"error", "hint"?}``.
    """
    try:
        breakpoints = bridge.debugger().breakpoints()
    except DebugError as exc:
        return debug_error(exc)
    return {"breakpoints": [_breakpoint_dict(bp) for bp in breakpoints]}


@mcp.tool()
def debug_slots() -> dict:
    """Report hardware watchpoint usage of the connected core.

    Returns:
        dict: ``{"core", "watchpoint_limit", "watchpoints_used", "free",
        "software_watchpoints", "by_kind", "watchpoints"}`` or
        ``{"error", "hint"?}``.
    """
    try:
        slots = Watchpoints(bridge.debugger()).slots()
    except DebugError as exc:
        return debug_error(exc)
    return {
        "core": slots.core,
        "watchpoint_limit": slots.limit,
        "watchpoints_used": slots.used,
        "free": slots.free,
        "software_watchpoints": len(slots.software),
        "by_kind": slots.by_kind,
        "watchpoints": [_breakpoint_dict(bp) for bp in slots.watchpoints],
    }


def _hit_list(result: dict) -> list[dict]:
    """Format hit-log entries with hex addresses and symbols."""
    hits = result.get("hits", [])
    symbols = bridge.symbols()
    formatted = []
    for hit in hits:
        pc = int(hit["pc"])
        symbol = symbols.resolve(pc)
        formatted.append(
            {
                "pc": f"0x{pc:08x}",
                "addr": f"0x{int(hit['addr']):08x}",
                "kind": hit.get("kind"),
                "pc_symbol": symbol.name if symbol else None,
            }
        )
    return formatted


@mcp.tool()
def hit_log_start(core: str = "arm9", capacity: int = 4096) -> dict:
    """Start recording breakpoint/watchpoint hits without stopping.

    Parameters:
        core (str): ``arm9`` or ``arm7``.
        capacity (int): Ring capacity (oldest hits dropped when full).

    Returns:
        dict: ``{"ok": true, "capacity": N}`` or ``{"error", "hint"?}``.
    """
    return control_call("gdb.hits.start", {"core": core, "capacity": capacity})


@mcp.tool()
def hit_log_stop(core: str = "arm9") -> dict:
    """Stop recording hits (existing hits stay readable).

    Parameters:
        core (str): ``arm9`` or ``arm7``.

    Returns:
        dict: ``{"ok": true}`` or ``{"error", "hint"?}``.
    """
    return control_call("gdb.hits.stop", {"core": core})


@mcp.tool()
def hit_log_clear(core: str = "arm9") -> dict:
    """Clear the hit log and its dropped counter.

    Parameters:
        core (str): ``arm9`` or ``arm7``.

    Returns:
        dict: ``{"ok": true}`` or ``{"error", "hint"?}``.
    """
    return control_call("gdb.hits.clear", {"core": core})


@mcp.tool()
def hit_log_read(core: str = "arm9", clear: bool = False) -> dict:
    """Read the hit log, optionally clearing it afterwards.

    Parameters:
        core (str): ``arm9`` or ``arm7``.
        clear (bool): Clear the log after a successful read.

    Returns:
        dict: ``{"count", "dropped", "hits": [{"pc", "addr", "kind"}]}`` or
        ``{"error", "hint"?}``.
    """
    result = control_call("gdb.hits.read", {"core": core})
    if "error" in result:
        return result
    hits = _hit_list(result)
    if clear:
        cleared = control_call("gdb.hits.clear", {"core": core})
        if "error" in cleared:
            return cleared
    return {
        "count": result.get("count", len(hits)),
        "dropped": result.get("dropped", 0),
        "hits": hits,
    }
