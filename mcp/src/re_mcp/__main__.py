"""Entry point: run the MCP server.

Transport is selected with ``MCP_TRANSPORT``:

- ``stdio`` (default): the client spawns the server (local MCP).
- ``streamable-http`` / ``sse``: a long-running network server, so it can be
  deployed once and connected to by the agent (``MCP_HOST`` / ``MCP_PORT``).
"""
import os

from .logging_setup import setup_logging
from .tools.server import mcp


def main() -> None:
    """Start the MCP server on the configured transport."""
    setup_logging()
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(
            transport="sse",
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8765")),
        )
    elif transport in ("streamable-http", "http"):
        mcp.run(
            transport="streamable-http",
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8765")),
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
