"""Ponto de entrada: roda o servidor MCP (transporte stdio)."""
from .tools.server import mcp


def main() -> None:
    """Inicia o servidor MCP por stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
