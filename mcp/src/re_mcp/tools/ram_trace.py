"""MCP tools for the CPU RAM write trace (addr, PC and value)."""
from ..application.ram_trace import RamTrace
from ..domain.ram_trace import RamWrite, RamWriteGroup
from ..infra.control import ControlError
from .app import bridge, error, mcp

_CONTROL_HINT = "Verifique se o melonDS está rodando com o canal de controle habilitado."
_NOT_IMPLEMENTED_HINT = (
    "O emulador não expõe ram.write_trace.*; reinicie com o build que inclui o PR #24."
)
_ZERO_HINT = (
    "Nenhum write coletado: a trace foi iniciada com ram_write_trace_start? "
    "O jogo rodou durante a coleta? JIT fastmem não é coberto."
)


def _control_hint(exc: ControlError) -> str:
    """Pick a hint for a failed control-channel call."""
    if "method not found" in str(exc).lower():
        return _NOT_IMPLEMENTED_HINT
    return _CONTROL_HINT


def _write_dict(write: RamWrite) -> dict:
    """Serialize one RAM write."""
    return {
        "cpu": "arm9" if write.cpu == 0 else "arm7",
        "addr": f"0x{write.addr:08x}",
        "value": f"0x{write.value:08x}",
        "width": write.width,
        "pc": f"0x{write.pc:08x}",
    }


def _group_dict(group: RamWriteGroup) -> dict:
    """Serialize one aggregated write group."""
    return {
        "cpu": "arm9" if group.cpu == 0 else "arm7",
        "addr": f"0x{group.addr:08x}",
        "width": group.width,
        "pc": f"0x{group.pc:08x}",
        "count": group.count,
    }


def _cpu_value(cpu: str | None) -> int | None:
    """Map an ``arm9``/``arm7`` name to the channel's CPU id.

    Raises:
        ValueError: If the name is unknown.
    """
    if cpu is None:
        return None
    key = cpu.lower()
    if key in ("arm9", "9"):
        return 0
    if key in ("arm7", "7"):
        return 1
    raise ValueError(f"cpu inválido: {cpu!r} (use 'arm9' ou 'arm7')")


@mcp.tool()
def ram_write_trace_start(
    addr_start: int,
    addr_end: int,
    batch: int = 256,
    timeout_ms: int = 100,
    max_items: int = 65536,
) -> dict:
    """Start the CPU RAM write trace for an address range.

    Records CPU data writes (``addr``, ``value``, ``width``, ``pc``) inside
    ``[addr_start, addr_end)``. Works with the GDB-enabled interpreter build.
    Collect with ``ram_write_trace_read`` or use ``watch_range``.

    Parameters:
        addr_start (int): First address (inclusive).
        addr_end (int): End address (exclusive).
        batch (int): Writes per batch.
        timeout_ms (int): Batch timeout in milliseconds.
        max_items (int): Ring capacity; the oldest writes are dropped past it.

    Returns:
        dict: ``{"ok": true, ...}`` or ``{"error": ...}``.
    """
    if addr_start >= addr_end:
        return error(ValueError("addr_start deve ser menor que addr_end"))
    try:
        channel = bridge.control()
        return RamTrace(channel).start(
            addr_start, addr_end, batch, timeout_ms, max_items
        )
    except ControlError as exc:
        return error(exc, _control_hint(exc))


@mcp.tool()
def ram_write_trace_read(
    seconds: float = 2.0,
    addr_start: int | None = None,
    addr_end: int | None = None,
    cpu: str | None = None,
    pc: int | None = None,
    max_items: int | None = None,
    summary: bool = False,
) -> dict:
    """Collect the CPU RAM writes for a period, optionally filtered/aggregated.

    Collects from an **already-started** trace; it never starts or restarts one.
    Call ``ram_write_trace_start`` first (or use ``watch_range``).

    Parameters:
        seconds (float): Collection duration in seconds.
        addr_start (int | None): Optional lower bound (inclusive).
        addr_end (int | None): Optional upper bound (exclusive).
        cpu (str | None): ``arm9`` or ``arm7``.
        pc (int | None): Only writes performed at this PC.
        max_items (int | None): Maximum number of writes to return.
        summary (bool): Aggregate by ``(addr, width, pc, cpu)``.

    Returns:
        dict: ``{"count", "writes"}`` or ``{"count", "groups"}``; or
        ``{"error", "hint"?}``.
    """
    if addr_start is not None and addr_end is not None and addr_start >= addr_end:
        return error(ValueError("addr_start deve ser menor que addr_end"))
    if max_items is not None and max_items <= 0:
        return error(ValueError("max_items deve ser > 0"), "Use um inteiro positivo.")
    try:
        cpu_value = _cpu_value(cpu)
        channel = bridge.control()
    except ValueError as exc:
        return error(exc, "Use 'arm9' ou 'arm7'.")
    except ControlError as exc:
        return error(exc, _control_hint(exc))
    trace = RamTrace(channel)
    try:
        writes = trace.collect(
            seconds,
            addr_start=addr_start,
            addr_end=addr_end,
            cpu=cpu_value,
            pc=pc,
            max_items=max_items,
        )
    except ControlError as exc:
        return error(exc, _control_hint(exc))
    if summary:
        out = {
            "count": len(writes),
            "groups": [_group_dict(group) for group in trace.summarize(writes)],
        }
    else:
        out = {"count": len(writes), "writes": [_write_dict(write) for write in writes]}
    if not writes:
        out["hint"] = _ZERO_HINT
    return out


@mcp.tool()
def ram_write_trace_stop() -> dict:
    """Stop the CPU RAM write trace.

    Returns:
        dict: ``{"ok": true}`` or ``{"error": ...}``.
    """
    try:
        channel = bridge.control()
        return RamTrace(channel).stop()
    except ControlError as exc:
        return error(exc, _control_hint(exc))


@mcp.tool()
def watch_range(
    addr_start: int,
    addr_end: int,
    seconds: float = 2.0,
    cpu: str | None = None,
    pc: int | None = None,
    max_items: int | None = None,
) -> dict:
    """Watch CPU writes in ``[addr_start, addr_end)`` for a period.

    Convenience wrapper: starts the trace, collects for ``seconds`` and stops.
    This is the only tool that starts/stops automatically; the game must be
    running during the collection window.

    Parameters:
        addr_start (int): First address (inclusive).
        addr_end (int): End address (exclusive).
        seconds (float): Collection duration in seconds.
        cpu (str | None): ``arm9`` or ``arm7``.
        pc (int | None): Only writes performed at this PC.
        max_items (int | None): Maximum number of writes to return.

    Returns:
        dict: ``{"count", "writes"}`` or ``{"error", "hint"?}``.
    """
    if addr_start >= addr_end:
        return error(ValueError("addr_start deve ser menor que addr_end"))
    try:
        cpu_value = _cpu_value(cpu)
        channel = bridge.control()
    except ValueError as exc:
        return error(exc, "Use 'arm9' ou 'arm7'.")
    except ControlError as exc:
        return error(exc, _control_hint(exc))
    trace = RamTrace(channel)
    try:
        started = trace.start(addr_start, addr_end)
        if "error" in started:
            return started
        writes = trace.collect(
            seconds,
            addr_start=addr_start,
            addr_end=addr_end,
            cpu=cpu_value,
            pc=pc,
            max_items=max_items,
        )
    except ControlError as exc:
        return error(exc, _control_hint(exc))
    finally:
        try:
            trace.stop()
        except ControlError:
            pass
    out = {"count": len(writes), "writes": [_write_dict(write) for write in writes]}
    if not writes:
        out["hint"] = _ZERO_HINT
    return out
