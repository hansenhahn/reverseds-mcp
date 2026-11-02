"""MCP tools for IO decoding: `io_read`."""
from ..application.io import IoReader, decode_register
from ..domain.io import UnknownRegister
from ..infra.gdb import DebugError
from .app import bridge, debug_error, error, mcp, reg_dict


@mcp.tool()
def io_read(addr: int, raw: int | None = None) -> dict:
    """Read and decode a memory-mapped IO register.

    The target must be **stopped** unless ``raw`` is provided. The register is decoded
    into named fields from the schema (DISPCNT, BGxCNT, scroll/window/mosaic/blend,
    DISP3DCNT, POWCNT1, VRAMCNT, DMA registers).

    Parameters:
        addr (int): The IO address (e.g. ``0x04000000`` for DISPCNT A).
        raw (int | None): Optional known value to decode **without** reading memory
            (useful for write-only registers and values from savestates/logs).

    Returns:
        dict: ``{"name", "address", "raw", "write_only", "fields": {...}}``, plus a
        ``hint`` for write-only reads that return 0; or ``{"error", "hint"?}``.
    """
    io_map = bridge.io_map()
    try:
        register = (
            decode_register(io_map, addr, raw)
            if raw is not None
            else IoReader(bridge.debugger(), io_map).read(addr)
        )
    except UnknownRegister as exc:
        return error(exc, "Use um endereço de IO coberto pelo schema (ex.: 0x04000000).")
    except ValueError as exc:
        return error(exc, "Use um valor que caiba no tamanho do registrador.")
    except DebugError as exc:
        return debug_error(exc)
    out = reg_dict(register)
    if register.write_only and register.raw == 0 and raw is None:
        out["hint"] = (
            "Registrador write-only: a leitura pode ser 0. Use raw=... com um valor "
            "conhecido (savestate/log) ou o estado do renderer."
        )
    return out
