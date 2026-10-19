"""Logging setup for the MCP (stderr, level configurable via ``RE_MCP_LOG_LEVEL``)."""
import logging
import os
import sys

_LEVELS = {"OFF": logging.CRITICAL + 1}


def level_from_env() -> int:
    """Resolve the log level from ``RE_MCP_LOG_LEVEL`` (default ``INFO``)."""
    name = os.environ.get("RE_MCP_LOG_LEVEL", "INFO").upper()
    if name in _LEVELS:
        return _LEVELS[name]
    return getattr(logging, name, logging.INFO)


def setup_logging() -> None:
    """Configure the ``re_mcp`` logger to ``stderr`` (captured by ``deploy.sh logs``)."""
    logger = logging.getLogger("re_mcp")
    logger.setLevel(level_from_env())
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
