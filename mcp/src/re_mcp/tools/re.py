"""MCP tools for RE workflows: watchpoints, snapshots and symbols."""
from ..application.args import ArgsOnHit
from ..application.contract import ContractChecks
from ..application.display import DisplayReader
from ..application.dma_trace import DmaTrace
from ..application.patches import PatchComparer
from ..application.snapshots import SnapshotError
from ..application.watchpoints import Watchpoints
from ..domain.addresses import AddressSpace
from ..domain.contract import Contract
from ..domain.patch import Patch
from ..domain.symbols import Symbol, SymbolTable
from ..domain.overlays import OverlayHit
from ..domain.structs import StructCandidate
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
        addr = AddressSpace.parse(value)
    except ValueError as exc:
        return error(exc, "Use hexadecimal (0x...) ou decimal (0..0xFFFFFFFF).")
    info = AddressSpace.describe(addr)
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
def args_on_hit(
    addr: int,
    condition: str | None = None,
    count: int = 1,
    timeout: float = 30.0,
    stack_words: int = 8,
    schema: dict[str, int | str] | None = None,
) -> dict:
    """Capture and check call arguments at a callsite.

    Arms a breakpoint, resumes, and captures ``r0..r3``, ``sp``, ``lr``, ``cpsr``
    and stack words on each hit. An optional schema compares values by argument:
    an integer means exact, and ``ptr``/``nonzero``/``zero`` are assertions.

    Parameters:
        addr (int): Callsite address.
        condition (str | None): Optional gdb condition.
        count (int): Maximum hits to capture (1..32).
        timeout (float): Timeout per hit, in seconds.
        stack_words (int): Number of 32-bit words read from ``sp`` (0..64).
        schema (dict[str, int | str] | None): Expected values by ``r0..r3``,
            ``sp``, ``lr``, ``cpsr`` or ``stackN``.

    Returns:
        dict: ``{"count", "hits": [...]}`` or ``{"error", "hint"?}``.
    """
    try:
        hits = ArgsOnHit(bridge.debugger()).collect(
            addr, condition, count, timeout, stack_words, schema
        )
    except DebugError as exc:
        return debug_error(exc)
    symbols = bridge.symbols()
    serialized = []
    for hit in hits:
        symbol = symbols.resolve(hit.pc)
        serialized.append(
            {
                "pc": hit.pc,
                "pc_hex": f"0x{hit.pc:08x}",
                "pc_symbol": symbol.name if symbol else None,
                "registers": hit.registers,
                "stack": list(hit.stack),
                "checks": [
                    {
                        "arg": check.arg,
                        "expected": check.expected,
                        "actual": check.actual,
                        "ok": check.ok,
                        "checked": check.checked,
                    }
                    for check in hit.checks
                ],
                "ok": hit.ok,
            }
        )
    return {"count": len(serialized), "hits": serialized}


@mcp.tool()
def contract_check(
    addr: int,
    schema: dict[str, int | str],
    ret_schema: dict[str, int | str] | None = None,
    condition: str | None = None,
    count: int = 1,
    timeout: float = 30.0,
    stack_words: int = 8,
) -> dict:
    """Validate a function contract against runtime values.

    Captures ``r0..r3``/stack at ``addr`` and compares with ``schema``. When
    ``ret_schema`` is given, also stops at the return address (``lr``) and checks
    the return registers (first return per invocation).

    Parameters:
        addr (int): Callsite address.
        schema (dict[str, int | str]): Expected arguments (name → value/token).
        ret_schema (dict[str, int | str] | None): Expected returns.
        condition (str | None): Optional gdb condition.
        count (int): Maximum invocations (1..32).
        timeout (float): Timeout per hit/return, in seconds.
        stack_words (int): Number of 32-bit words read from ``sp`` (0..64).

    Returns:
        dict: ``{"callsite", "ok", "count", "hits", "divergences"}`` or
        ``{"error", "hint"?}``.
    """
    try:
        contract = Contract.from_schema(schema, ret_schema)
        hits = ContractChecks(bridge.debugger()).run(
            addr, contract, condition, count, timeout, stack_words
        )
    except DebugError as exc:
        return debug_error(exc)
    symbols = bridge.symbols()
    symbol = symbols.resolve(addr)
    serialized = []
    divergences: list[dict] = []
    for hit in hits:
        entry = hit.entry
        returned = hit.returned
        serialized.append(
            {
                "pc": entry.pc,
                "pc_hex": f"0x{entry.pc:08x}",
                "registers": entry.registers,
                "stack": list(entry.stack),
                "checks": [
                    {
                        "arg": check.arg,
                        "expected": check.expected,
                        "actual": check.actual,
                        "ok": check.ok,
                        "checked": check.checked,
                    }
                    for check in entry.checks
                ],
                "return": (
                    None
                    if returned is None
                    else {
                        "registers": returned.registers,
                        "checks": [
                            {
                                "arg": check.arg,
                                "expected": check.expected,
                                "actual": check.actual,
                                "ok": check.ok,
                                "checked": check.checked,
                            }
                            for check in returned.checks
                        ],
                        "ok": returned.ok,
                    }
                ),
                "ok": hit.ok,
            }
        )
        for check in entry.checks:
            if not check.ok:
                divergences.append(
                    {
                        "kind": "arg",
                        "pc": f"0x{entry.pc:08x}",
                        "arg": check.arg,
                        "expected": check.expected,
                        "actual": check.actual,
                        "checked": check.checked,
                    }
                )
        if hit.returns_expected:
            if returned is None:
                divergences.append(
                    {
                        "kind": "return",
                        "pc": f"0x{entry.pc:08x}",
                        "missing": True,
                    }
                )
            else:
                for check in returned.checks:
                    if not check.ok:
                        divergences.append(
                            {
                                "kind": "return",
                                "pc": f"0x{entry.pc:08x}",
                                "arg": check.arg,
                                "expected": check.expected,
                                "actual": check.actual,
                                "checked": check.checked,
                            }
                        )
    return {
        "callsite": addr,
        "callsite_hex": f"0x{addr:08x}",
        "callsite_symbol": symbol.name if symbol else None,
        "schema": schema,
        "ret_schema": ret_schema,
        "count": len(serialized),
        "ok": bool(serialized) and all(hit.ok for hit in hits),
        "hits": serialized,
        "divergences": divergences,
    }


@mcp.tool()
def field_xref(
    base: int | str,
    offset: int,
    kind: str = "write",
    timeout: float = 30.0,
    condition: str | None = None,
) -> dict:
    """Observe reads/writes to a field ``base + offset`` (runtime watchpoint).

    Parameters:
        base (int | str): Struct base address or symbol name.
        offset (int): Field offset.
        kind (str): ``write`` or ``read``.
        timeout (float): Maximum wait time in seconds.
        condition (str | None): Optional gdb condition.

    Returns:
        dict: ``{"field", "base", "offset", "kind", "hit"}`` or ``{"error", ...}``.
    """
    base_symbol = None
    if isinstance(base, str):
        symbol = bridge.symbols().by_name(base)
        if symbol is None:
            return {"error": f"símbolo não encontrado: {base}"}
        base_addr = symbol.addr
        base_symbol = symbol.name
    else:
        base_addr = base
    if kind not in ("write", "read"):
        return {"error": "kind deve ser 'write' ou 'read'"}
    field = base_addr + offset
    try:
        watchpoints = Watchpoints(bridge.debugger())
        hit = (
            watchpoints.find_write(field, timeout, condition)
            if kind == "write"
            else watchpoints.find_read(field, timeout, condition)
        )
    except DebugError as exc:
        return debug_error(exc)
    result = {
        "field": f"0x{field:08x}",
        "base": base_addr,
        "base_symbol": base_symbol,
        "offset": offset,
        "kind": kind,
    }
    if hit is None:
        result["hit"] = None
        return result
    symbol = bridge.symbols().resolve(hit.pc)
    result["hit"] = {
        "pc": hit.pc,
        "pc_hex": f"0x{hit.pc:08x}",
        "pc_symbol": symbol.name if symbol else None,
        "registers": hit.registers,
    }
    return result


@mcp.tool()
def field_writers(
    base: int | str, offset: int, timeout: float = 30.0, condition: str | None = None
) -> dict:
    """Convenience: writers of ``base + offset`` (see `field_xref`)."""
    return field_xref(base, offset, "write", timeout, condition)


@mcp.tool()
def struct_candidate(code: int, size: int = 0x200, mode: str = "arm") -> dict:
    """Infer a candidate struct from loads/stores in a code range.

    Scans ``[rN, #imm]`` accesses (ignoring ``sp``/``pc``), groups by offset with
    the maximum width/registers and renders a C skeleton with padding. The result
    is an over-approximation (any register may be the base).

    Parameters:
        code (int): Code start address.
        size (int): Number of bytes to scan (1..16384).
        mode (str): ``arm`` or ``thumb``.

    Returns:
        dict: ``{"code", "mode", "size", "fields", "c"}`` or ``{"error", ...}``.
    """
    size = max(1, min(size, 0x4000))
    try:
        data = bridge.debugger().read_memory(code, size)
    except DebugError as exc:
        return debug_error(exc)
    try:
        candidate = StructCandidate.scan(data, code, mode)
    except ValueError as exc:
        return {"error": str(exc)}
    return {
        "code": code,
        "mode": mode,
        "size": len(data),
        "fields": [
            {
                "offset": field.offset,
                "width": field.width,
                "registers": list(field.registers),
                "accesses": field.accesses,
            }
            for field in candidate.fields
        ],
        "c": candidate.render_c(),
    }


@mcp.tool()
def diff_patch(asm_patch: list[dict], c_equiv: list[dict]) -> dict:
    """Compare the bytes produced by an ASM patch and its C equivalent.

    Each patch is a list of ``{addr, bytes}`` writes (``bytes`` in hex). The tool
    reads the current memory over the touched ranges, applies both patches to a
    copy and reports every differing byte. It does not execute either patch.

    Parameters:
        asm_patch (list[dict]): ASM patch writes.
        c_equiv (list[dict]): Compiled C-equivalent writes.

    Returns:
        dict: ``{"mode", "iguais", "count", "diffs", "regions"}`` or ``{"error"}``.
    """
    try:
        asm, c_equiv_patch, diff = PatchComparer(bridge.debugger()).compare(
            asm_patch, c_equiv
        )
    except ValueError as exc:
        return {"error": str(exc)}
    except DebugError as exc:
        return debug_error(exc)
    limit = 2048
    shown = diff.diffs[:limit]
    return {
        "mode": "static",
        "iguais": diff.iguais,
        "count": len(diff.diffs),
        "truncated": len(diff.diffs) > limit,
        "diffs": [
            {
                "addr": f"0x{item.addr:08x}",
                "asm": item.asm,
                "c": item.c,
            }
            for item in shown
        ],
        "regions": [
            {
                "start": f"0x{start:08x}",
                "end": f"0x{end:08x}",
            }
            for start, end in Patch.merged_regions(asm, c_equiv_patch)
        ],
    }


@mcp.tool()
def map_cell(engine: str = "A", bg: int = 0, x: int = 0, y: int = 0) -> dict:
    """Resolve a BG cell to its map entry, tile index and tile address.

    Parameters:
        engine (str): ``A`` or ``B``.
        bg (int): BG layer 0..3.
        x (int): X pixel in the BG map.
        y (int): Y pixel in the BG map.

    Returns:
        dict: Cell details or ``{"error", "hint"?}``.
    """
    try:
        cell = DisplayReader(bridge.debugger(), bridge.io_map()).map_cell(
            engine, bg, x, y
        )
    except DebugError as exc:
        return debug_error(exc)
    except ValueError as exc:
        return error(exc, "Confira engine/BG e coordenadas; só text/affine são suportados.")
    return {
        "engine": cell.engine,
        "bg": cell.bg,
        "kind": cell.kind,
        "x": cell.x,
        "y": cell.y,
        "cell": [cell.cell_x, cell.cell_y],
        "entry_addr": f"0x{cell.entry_addr:08x}",
        "entry": f"0x{cell.entry:04x}",
        "tile_index": cell.tile_index,
        "tile_addr": f"0x{cell.tile_addr:08x}",
        "palette": cell.palette,
        "bpp": cell.bpp,
        "flip_h": cell.flip_h,
        "flip_v": cell.flip_v,
        "char_base": f"0x{cell.char_base:08x}",
        "screen_base": f"0x{cell.screen_base:08x}",
        "map_size": [cell.map_width, cell.map_height],
    }


@mcp.tool()
def vram_tile_bytes(
    engine: str = "A",
    tile_index: int = 0,
    layer: str = "bg",
    bg: int = 0,
    bpp: int | None = None,
) -> dict:
    """Read the bytes of a BG or OBJ tile (4bpp/8bpp).

    Parameters:
        engine (str): ``A`` or ``B``.
        tile_index (int): Tile number.
        layer (str): ``bg`` or ``obj``.
        bg (int): BG layer (for ``layer="bg"``).
        bpp (int | None): OBJ color depth (4/8; default 4).

    Returns:
        dict: ``{"addr", "bpp", "size", "hex"}`` or ``{"error", ...}``.
    """
    try:
        addr, depth, data = DisplayReader(
            bridge.debugger(), bridge.io_map()
        ).tile_bytes(engine, tile_index, layer, bg, bpp)
    except DebugError as exc:
        return debug_error(exc)
    except ValueError as exc:
        return error(exc)
    return {
        "addr": f"0x{addr:08x}",
        "bpp": depth,
        "size": len(data),
        "hex": data.hex(),
    }


@mcp.tool()
def find_tile_in_ram(
    engine: str = "A",
    tile_index: int = 0,
    layer: str = "bg",
    bg: int = 0,
    bpp: int | None = None,
    ram_addr: int = 0x02000000,
    ram_size: int = 0x400000,
) -> dict:
    """Find the bytes of a VRAM tile inside RAM.

    Parameters:
        engine (str): ``A`` or ``B``.
        tile_index (int): Tile number.
        layer (str): ``bg`` or ``obj``.
        bg (int): BG layer (for ``layer="bg"``).
        bpp (int | None): OBJ color depth (4/8; default 4).
        ram_addr (int): RAM start to search.
        ram_size (int): Bytes to search (max 4 MiB).

    Returns:
        dict: ``{"tile_addr", "bpp", "count", "addresses", "ram"}`` or ``{"error", ...}``.
    """
    try:
        tile_addr, depth, addresses = DisplayReader(
            bridge.debugger(), bridge.io_map()
        ).find_tile_in_ram(engine, tile_index, layer, bg, bpp, ram_addr, ram_size)
    except DebugError as exc:
        return debug_error(exc)
    except ValueError as exc:
        return error(exc)
    return {
        "tile_addr": f"0x{tile_addr:08x}",
        "bpp": depth,
        "count": len(addresses),
        "addresses": [f"0x{addr:08x}" for addr in addresses],
        "ram": {"addr": f"0x{ram_addr:08x}", "size": ram_size},
    }


@mcp.tool()
def dma_source(
    vram_addr: int, seconds: float = 2.0, batch: int = 256, timeout_ms: int = 100
) -> dict:
    """Collect DMA transfers that wrote a VRAM address in a time window.

    Parameters:
        vram_addr (int): Destination VRAM address.
        seconds (float): Collection duration.
        batch (int): Events per batch.
        timeout_ms (int): Batch timeout.

    Returns:
        dict: ``{"vram_addr", "count", "hits": [...]}`` or ``{"error", ...}``.
    """
    try:
        channel = bridge.control()
    except ControlError as exc:
        return error(
            exc, "Verifique se o melonDS está rodando com o canal de controle habilitado."
        )
    try:
        transfers = DmaTrace(channel).find_destination(
            vram_addr, seconds, batch, timeout_ms
        )
    except ControlError as exc:
        return error(exc)
    symbols = bridge.symbols()
    hits = []
    for transfer in transfers:
        symbol = symbols.resolve(transfer.pc)
        hits.append(
            {
                "channel": transfer.channel,
                "cpu": "arm9" if transfer.cpu == 0 else "arm7",
                "src": f"0x{transfer.source.address:08x}",
                "dst": f"0x{transfer.destination.address:08x}",
                "length": transfer.length,
                "pc": f"0x{transfer.pc:08x}",
                "pc_symbol": symbol.name if symbol else None,
            }
        )
    return {"vram_addr": f"0x{vram_addr:08x}", "count": len(hits), "hits": hits}


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
