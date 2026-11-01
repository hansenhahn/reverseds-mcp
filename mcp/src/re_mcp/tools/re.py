"""MCP tools for RE workflows: watchpoints, snapshots and symbols."""
from ..application.snapshots import SnapshotError
from ..application.watchpoints import Watchpoints
from ..domain.addresses import describe_address, parse_address
from ..domain.symbols import Symbol, SymbolTable
from ..domain.overlays import OverlayHit
from ..infra.control import ControlError
from ..infra.gdb import DebugError
from ..infra.ndsrom import NdsRomError
from .app import bridge, debug_error, error, mcp


def _overlay_dict(hit: OverlayHit) -> dict:
    """Serialize an overlay hit for a tool response."""
    overlay = hit.overlay
    return {
        "core": overlay.core,
        "index": overlay.index,
        "ram_address": overlay.ram_address,
        "ram_size": overlay.ram_size,
        "bss_size": overlay.bss_size,
        "file_id": overlay.file_id,
        "offset": hit.offset,
    }


@mcp.tool()
def addr_valid(value: str | int) -> dict:
    """Validate/normalize an ARM9 address and resolve its region and overlay.

    Parameters:
        value (str | int): Address as ``0x``-hex, decimal text or integer.

    Returns:
        dict: ``{"value_dec", "value_hex", "aligned4", "mapped", "region",
        "overlay"}`` or ``{"error", "hint"?}``.
    """
    try:
        addr = parse_address(value)
    except ValueError as exc:
        return error(exc, "Use hexadecimal (0x...) ou decimal (0..0xFFFFFFFF).")
    info = describe_address(addr)
    overlay: dict | None = None
    try:
        hit = bridge.overlays().overlay_for_address(addr)
    except (NdsRomError, ControlError):
        hit = None
    if hit is not None:
        overlay = _overlay_dict(hit)
    symbol = bridge.symbols().resolve(addr)
    return {
        "value_dec": info.value,
        "value_hex": info.value_hex,
        "aligned4": info.aligned4,
        "mapped": info.mapped,
        "region": info.region.name if info.region else None,
        "overlay": overlay,
        "symbol": symbol.name if symbol else None,
    }


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
    symbol = bridge.symbols().resolve(hit.pc)
    return {"hit": {"pc": hit.pc, "pc_hex": f"0x{hit.pc:08x}",
                    "pc_symbol": symbol.name if symbol else None,
                    "registers": hit.registers}}


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
    symbol = bridge.symbols().resolve(hit.pc)
    return {"hit": {"pc": hit.pc, "pc_hex": f"0x{hit.pc:08x}",
                    "pc_symbol": symbol.name if symbol else None,
                    "registers": hit.registers}}


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
def symbol_define(
    addr: int,
    name: str,
    kind: str = "function",
    comment: str | None = None,
    overlay: int | None = None,
) -> dict:
    """Define a persistent symbol/alias for an address.

    Parameters:
        addr (int): Address.
        name (str): Symbol name.
        kind (str): ``function``, ``label``, ``data``, ``struct`` or a free-form kind.
        comment (str | None): Optional note.
        overlay (int | None): Optional overlay id (metadata; resolution is by address).

    Returns:
        dict: ``{"ok": true, "addr", "name", "kind", "count", "path"}`` or ``{"error": ...}``.
    """
    path = bridge.add_symbol(Symbol(addr, name, kind, comment, overlay))
    return {
        "ok": True,
        "addr": f"0x{addr:08x}",
        "name": name,
        "kind": kind,
        "count": len(bridge.symbols()),
        "path": path,
    }


@mcp.tool()
def symbol_list(kind: str | None = None) -> dict:
    """List persistent symbols, optionally filtered by kind.

    Parameters:
        kind (str | None): Optional kind filter.

    Returns:
        dict: ``{"count": N, "symbols": [...]}``.
    """
    symbols = bridge.symbols().all()
    if kind:
        symbols = [symbol for symbol in symbols if symbol.kind == kind]
    return {
        "count": len(symbols),
        "symbols": [
            {
                "addr": f"0x{symbol.addr:08x}",
                "name": symbol.name,
                "kind": symbol.kind,
                "comment": symbol.comment,
                "overlay": symbol.overlay,
            }
            for symbol in symbols
        ],
    }


@mcp.tool()
def symbol_load(path: str, merge: bool = True) -> dict:
    """Load a symbol map (`.map`), merging with the persistent table by default.

    Parameters:
        path (str): Path to the `.map` file (lines ``address name``).
        merge (bool): Merge into the current table (default) or replace it.

    Returns:
        dict: ``{"ok": true, "count": N, "path": ...}`` or ``{"error": ...}``.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            table = SymbolTable.from_map(handle.read())
    except OSError as exc:
        return {"error": str(exc)}
    if merge:
        bridge.symbols().merge(table)
    else:
        bridge.set_symbols(table)
    out_path = bridge.save_symbols()
    return {"ok": True, "count": len(bridge.symbols()), "path": out_path}


@mcp.tool()
def symbol_lookup(addr: int) -> dict:
    """Resolve an address to the symbol containing it.

    Parameters:
        addr (int): Address to look up.

    Returns:
        dict: ``{"name", "addr", "addr_hex", "kind", "comment", "overlay"}`` or
        ``{"error": ...}``.
    """
    symbol = bridge.symbols().resolve(addr)
    if symbol is None:
        return {"error": "nenhum símbolo contém esse endereço"}
    return {
        "name": symbol.name,
        "addr": symbol.addr,
        "addr_hex": f"0x{symbol.addr:08x}",
        "kind": symbol.kind,
        "comment": symbol.comment,
        "overlay": symbol.overlay,
    }


@mcp.tool()
def decomp_snippet(addr: int, c: str | None = None, asm: str | None = None) -> dict:
    """Register or query a decomp snippet (C + ASM) by address.

    Parameters:
        addr (int): Address.
        c (str | None): C text to store (None keeps the current value).
        asm (str | None): ASM text to store (None keeps the current value).

    Returns:
        dict: ``{"addr", "c", "asm"}`` or ``{"error", "hint"?}``.
    """
    if c is None and asm is None:
        snippet = bridge.decomp().get(addr)
        if snippet is None:
            return {
                "error": "nenhum snippet nesse endereço",
                "hint": "Passe c/asm para registrar.",
            }
        return {"addr": snippet.addr, "c": snippet.c, "asm": snippet.asm}
    snippet = bridge.decomp().put(addr, c, asm)
    return {"ok": True, "addr": snippet.addr, "c": snippet.c, "asm": snippet.asm}
