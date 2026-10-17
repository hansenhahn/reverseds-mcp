"""Entry point: run the MCP server (stdio transport)."""
from .tools.server import mcp


def main() -> None:
    """Start the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
