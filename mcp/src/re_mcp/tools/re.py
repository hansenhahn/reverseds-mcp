"""Tools MCP de workflows de RE: watchpoints, snapshots e símbolos."""
from ..domain.debug import SnapshotError, Watchpoints
from ..domain.symbols import SymbolTable
from ..infra.gdb import DebugError
from .app import bridge, debug_error, mcp


@mcp.tool()
def find_writer(addr: int, timeout: float = 30.0, condition: str | None = None) -> dict:
    """Acha o código que ESCREVE num endereço (watchpoint de escrita + run).

    Parameters:
        addr (int): Endereço vigiado.
        timeout (float): Tempo máximo de espera em segundos.
        condition (str | None): Expressão gdb opcional; só para quando verdadeira
            (ex.: ``*(unsigned short*)0x0600F448 != 0`` para pular escritas de 0).

    Returns:
        dict: ``{"hit": {"pc", "registers"}}`` se parou, ``{"hit": null}`` se não houve
        escrita no prazo, ou ``{"error": ...}``.
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
    """Acha o código que LÊ um endereço (watchpoint de leitura + run).

    Parameters:
        addr (int): Endereço vigiado.
        timeout (float): Tempo máximo de espera em segundos.
        condition (str | None): Expressão gdb opcional; só para quando verdadeira.

    Returns:
        dict: ``{"hit": {"pc", "registers"}}`` se parou, ``{"hit": null}`` se não houve
        leitura no prazo, ou ``{"error": ...}``.
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
    """Guarda um bloco de memória para comparar depois (`state_diff`).

    Parameters:
        name (str): Nome da captura.
        addr (int): Endereço base.
        size (int): Tamanho em bytes.

    Returns:
        dict: ``{"ok": true, "name": ..., "size": ...}`` ou ``{"error": ...}``.
    """
    try:
        snapshot = bridge.snapshots().capture(name, addr, size)
    except DebugError as exc:
        return debug_error(exc)
    return {"ok": True, "name": name, "size": len(snapshot.data)}


@mcp.tool()
def state_diff(name: str) -> dict:
    """Compara a memória atual com uma captura (`mem_snapshot`) e lista o que mudou.

    Parameters:
        name (str): Nome da captura a comparar.

    Returns:
        dict: ``{"changes": [...], "count": N}`` ou ``{"error": ...}``.
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
    """Carrega um mapa de símbolos (`.map`) para resolver endereços.

    Parameters:
        path (str): Caminho do arquivo `.map` (linhas ``endereço nome``).

    Returns:
        dict: ``{"ok": true, "count": N}`` ou ``{"error": ...}``.
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
    """Resolve um endereço para o símbolo que o contém.

    Parameters:
        addr (int): Endereço consultado.

    Returns:
        dict: ``{"name": ..., "addr": ...}`` ou ``{"error": ...}``.
    """
    symbol = bridge.symbols().resolve(addr)
    if symbol is None:
        return {"error": "nenhum símbolo contém esse endereço"}
    return {"name": symbol.name, "addr": symbol.addr, "addr_hex": f"0x{symbol.addr:08x}"}
