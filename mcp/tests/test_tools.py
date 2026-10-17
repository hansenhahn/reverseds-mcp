"""Testes do servidor MCP (descoberta de tools e ponte)."""
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
    """O servidor MCP expõe a tool `ping`."""
    names = asyncio.run(_list_tools())
    assert "ping" in names


def test_lists_p0_tools() -> None:
    """As tools do roadmap P0 estão expostas (run não-bloqueante + dump em arquivo)."""
    names = asyncio.run(_list_tools())
    for tool in ("debug_resume", "debug_wait", "mem_dump_file"):
        assert tool in names
