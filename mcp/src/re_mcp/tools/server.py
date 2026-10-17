"""Servidor MCP: compõe as tools dos domínios.

As tools ficam em módulos por domínio (`control`, `debug`, `cart`, `re`); importá-los
aqui registra todas no `mcp` (via `@mcp.tool()`).
"""
from .app import bridge, debug_error, error, mcp
from . import cart, control, debug, re  # noqa: F401

__all__ = ["bridge", "debug_error", "error", "mcp"]
