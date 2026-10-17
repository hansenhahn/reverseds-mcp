"""MCP server: composes the domain tools.

The tools live in per-domain modules (`control`, `debug`, `cart`, `re`); importing
them here registers all of them in `mcp` (via `@mcp.tool()`).
"""
from .app import bridge, debug_error, error, mcp
from . import cart, control, debug, re  # noqa: F401

__all__ = ["bridge", "debug_error", "error", "mcp"]
