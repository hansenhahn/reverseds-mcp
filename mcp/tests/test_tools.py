"""MCP server tests (tool discovery and bridge)."""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _list_tools() -> list[str]:
    params = StdioServerParameters(command=sys.executable, args=["-m", "re_mcp"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [tool.name for tool in result.tools]


def test_lists_ping_tool() -> None:
    """The MCP server exposes the `ping` tool."""
    names = asyncio.run(_list_tools())
    assert "ping" in names


def test_lists_p0_tools() -> None:
    """The roadmap P0 tools are exposed (non-blocking run + file dump)."""
    names = asyncio.run(_list_tools())
    for tool in ("debug_resume", "debug_wait", "mem_dump_file"):
        assert tool in names


def test_lists_p1_tools() -> None:
    """The P1 change tools (input macros, disassemble, health-check) are exposed."""
    names = asyncio.run(_list_tools())
    for tool in ("input_tap", "input_sequence", "disassemble", "health_check"):
        assert tool in names


def test_lists_observability_tools() -> None:
    """The observability tools are exposed (backtrace, breakpoints)."""
    names = asyncio.run(_list_tools())
    for tool in ("debug_backtrace", "list_breakpoints"):
        assert tool in names


def test_lists_rom_info_tool() -> None:
    """The loaded-ROM identity tool is exposed."""
    assert "rom_info" in asyncio.run(_list_tools())


def test_lists_confidence_tools() -> None:
    """Wave 0 tools are exposed (slots and address validation)."""
    names = asyncio.run(_list_tools())
    for tool in ("debug_slots", "addr_valid"):
        assert tool in names


def test_lists_causal_runtime_tools() -> None:
    """Cold reset and hit-log tools are exposed."""
    names = asyncio.run(_list_tools())
    for tool in ("emu_reset", "hit_log_start", "hit_log_stop", "hit_log_read", "hit_log_clear"):
        assert tool in names


def test_lists_re_model_tools() -> None:
    """Symbols/aliases and decomp snippets are exposed."""
    names = asyncio.run(_list_tools())
    for tool in ("symbol_define", "symbol_list", "symbol_load", "symbol_lookup", "decomp_snippet"):
        assert tool in names
