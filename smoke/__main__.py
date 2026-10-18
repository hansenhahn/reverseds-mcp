"""Entry point: ``uv run --project mcp python -m smoke``."""
from .runner import main

if __name__ == "__main__":
    raise SystemExit(main())
