"""MCP tools for RE workflows: watchpoints, snapshots and symbols."""
from ..application.snapshots import SnapshotError
from ..application.watchpoints import Watchpoints
from ..domain.symbols import SymbolTable
from ..infra.gdb import DebugError
from .app import bridge, debug_error, mcp


@mcp.tool()
def find_writer(addr: int, timeout: float = 30.0, condition: str | None = None) -> dict:
    """Find the code that WRITES to an address (write watchpoint + run).

    Parameters:
        addr (int): Watched address.
        timeout (float): Maximum wait time in seconds.
        condition (str | None): Optional gdb expression; only stops when true
            (e.g. ``*(unsigned short*)0x0600F448 != 0`` to skip zero writes).

    Returns:
        dict: ``{"hit": {"pc", "registers"}}`` if it stopped, ``{"hit": null}`` if
        there was no write in time, or ``{"error": ...}``.
    """
    try:
        hit = Watchpoints(bridge.debugger()).find_write(addr, timeout, condition)
    except DebugError as exc:
        return debug_error(exc)
    if hit is None:
        return {"hit": None}
    return {"hit": {"pc": hit.pc, "pc_hex": f"0x{hit.pc:08x}", "registers": hit.registers}}


@mcp.tool()
def find_reader(addr: int, timeout: float = 30.0, condition: str | None = None) -> dict:
    """Find the code that READS an address (read watchpoint + run).

    Parameters:
        addr (int): Watched address.
        timeout (float): Maximum wait time in seconds.
        condition (str | None): Optional gdb expression; only stops when true.

    Returns:
        dict: ``{"hit": {"pc", "registers"}}`` if it stopped, ``{"hit": null}`` if
        there was no read in time, or ``{"error": ...}``.
    """
    try:
        hit = Watchpoints(bridge.debugger()).find_read(addr, timeout, condition)
    except DebugError as exc:
        return debug_error(exc)
    if hit is None:
        return {"hit": None}
    return {"hit": {"pc": hit.pc, "pc_hex": f"0x{hit.pc:08x}", "registers": hit.registers}}


@mcp.tool()
def mem_snapshot(name: str, addr: int, size: int) -> dict:
    """Store a block of memory for comparing later (`state_diff`).

    Parameters:
        name (str): Capture name.
        addr (int): Base address.
        size (int): Size in bytes.

    Returns:
        dict: ``{"ok": true, "name": ..., "size": ...}`` or ``{"error": ...}``.
    """
    try:
        snapshot = bridge.snapshots().capture(name, addr, size)
    except DebugError as exc:
        return debug_error(exc)
    return {"ok": True, "name": name, "size": len(snapshot.data)}


@mcp.tool()
def state_diff(name: str) -> dict:
    """Compare current memory with a capture (`mem_snapshot`) and list what changed.

    Parameters:
        name (str): The capture name to compare against.

    Returns:
        dict: ``{"changes": [...], "count": N}`` or ``{"error": ...}``.
    """
    try:
        diff = bridge.snapshots().diff(name)
    except SnapshotError as exc:
        return {"error": str(exc)}
    except DebugError as exc:
        return debug_error(exc)
    changes = [{"addr": c.addr, "old": c.old, "new": c.new} for c in diff.changes]
    return {"changes": changes, "count": len(changes)}


@mcp.tool()
def symbol_load(path: str) -> dict:
    """Load a symbol map (`.map`) to resolve addresses.

    Parameters:
        path (str): Path to the `.map` file (lines ``address name``).

    Returns:
        dict: ``{"ok": true, "count": N}`` or ``{"error": ...}``.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            table = SymbolTable.from_map(handle.read())
    except OSError as exc:
        return {"error": str(exc)}
    bridge.set_symbols(table)
    return {"ok": True, "count": len(table)}


@mcp.tool()
def symbol_lookup(addr: int) -> dict:
    """Resolve an address to the symbol containing it.

    Parameters:
        addr (int): Address to look up.

    Returns:
        dict: ``{"name": ..., "addr": ...}`` or ``{"error": ...}``.
    """
    symbol = bridge.symbols().resolve(addr)
    if symbol is None:
        return {"error": "nenhum símbolo contém esse endereço"}
    return {"name": symbol.name, "addr": symbol.addr, "addr_hex": f"0x{symbol.addr:08x}"}
