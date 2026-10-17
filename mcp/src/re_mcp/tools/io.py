"""MCP tools for IO decoding: `io_read`."""
from ..application.io import IoReader
from ..domain.io import UnknownRegister
from ..infra.gdb import DebugError
from .app import bridge, debug_error, error, mcp, reg_dict


@mcp.tool()
def io_read(addr: int) -> dict:
    """Read and decode a memory-mapped IO register.

    The target must be **stopped**. The register is decoded into named fields from the
    schema (e.g. DISPCNT, DISP3DCNT, POWCNT1, VRAMCNT, DMA registers).

    Parameters:
        addr (int): The IO address (e.g. ``0x04000000`` for DISPCNT A).

    Returns:
        dict: ``{"name", "address", "raw", "fields": {...}}`` or ``{"error", "hint"?}``.
    """
    try:
        register = IoReader(bridge.debugger(), bridge.io_map()).read(addr)
    except UnknownRegister as exc:
        return error(exc, "Use um endereço de IO coberto pelo schema (ex.: 0x04000000).")
    except DebugError as exc:
        return debug_error(exc)
    return reg_dict(register)
