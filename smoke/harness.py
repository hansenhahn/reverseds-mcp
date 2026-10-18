"""Harness primitives: emulator lifecycle, MCP stdio client and assertions.

The emulator is booted headless and the MCP is spawned from source
(``uv run --project mcp python -m re_mcp``) and spoken to over stdio, so the
tests exercise the same entry point the container runs without its lifecycle.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Iterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_DIR = REPO_ROOT / "mcp"
DEFAULT_MELONDS = REPO_ROOT.parent / "melonDS" / "build" / "melonDS"


def _config_socket() -> str | None:
    """Read the control socket path from the melonDS config, when present."""
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    config = base / "melonDS" / "melonDS.toml"
    if not config.exists():
        return None
    in_control = False
    for line in config.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_control = stripped == "[Control]"
            continue
        if in_control and stripped.startswith("Socket"):
            return stripped.partition("=")[2].strip().strip('"')
    return None


def resolve_socket() -> str:
    """Resolve the control socket: env override, else the melonDS config."""
    return (
        os.environ.get("RE_MCP_CONTROL_SOCKET")
        or _config_socket()
        or "/tmp/melonds-control.sock"
    )


DEFAULT_SOCKET = resolve_socket()


class SmokeError(AssertionError):
    """A smoke assertion failed."""


def check(condition: bool, message: str) -> None:
    """Assert a condition, raising `SmokeError` with a message when false."""
    if not condition:
        raise SmokeError(message)


@dataclass
class Emulator:
    """A headless melonDS process exposing the control socket and GDB stub."""

    rom: Path
    socket: str
    binary: Path
    log: Path
    proc: subprocess.Popen[bytes] = field(init=False)

    def start(self, boot_seconds: float = 6.0) -> "Emulator":
        """Kill any running instance, boot headless and wait for the socket."""
        self.kill_existing()
        if Path(self.socket).exists():
            Path(self.socket).unlink()
        env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "LIBGL_ALWAYS_SOFTWARE": "1"}
        handle = self.log.open("wb")
        self.proc = subprocess.Popen(
            [str(self.binary), str(self.rom)],
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        deadline = time.monotonic() + boot_seconds + 20
        while time.monotonic() < deadline:
            if Path(self.socket).exists():
                time.sleep(boot_seconds)
                return self
            if self.proc.poll() is not None:
                raise SmokeError(
                    f"melonDS morreu no boot (ver {self.log}):\n{self.log.read_text()[-2000:]}"
                )
            time.sleep(0.25)
        raise SmokeError(f"socket {self.socket} não apareceu (ver {self.log})")

    def stop(self) -> None:
        """Kill the emulator and drop the control socket."""
        if self.proc.poll() is None:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        if Path(self.socket).exists():
            Path(self.socket).unlink()

    @staticmethod
    def kill_existing() -> None:
        """Kill any melonDS already running (single-instance assumption)."""
        subprocess.run(["pkill", "-9", "-x", "melonDS"], check=False)


@dataclass
class Ctx:
    """Shared context passed to every case."""

    rom: Path
    socket: str
    out_dir: Path

    def session(self) -> object:
        """Open a fresh MCP server session (async context manager)."""
        return self._session()

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        env = {
            **os.environ,
            "RE_MCP_CONTROL_SOCKET": self.socket,
            "RE_MCP_ROM": str(self.rom),
            "RE_MCP_OUT_DIR": str(self.out_dir),
        }
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "re_mcp"],
            env=env,
            cwd=str(REPO_ROOT),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


async def call(session: ClientSession, tool: str, **args: object) -> dict:
    """Invoke an MCP tool and return its structured dict result."""
    result = await session.call_tool(tool, args)
    structured = getattr(result, "structuredContent", None)
    if structured:
        return structured
    for item in result.content:
        text = getattr(item, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text}
    return {}


async def tool_names(session: ClientSession) -> set[str]:
    """Return the names of the tools the MCP exposes."""
    listing = await session.list_tools()
    return {tool.name for tool in listing.tools}


def sha256(path: str) -> str:
    """Hash a file (used to compare captures deterministically)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def iter_cases() -> Iterator[object]:
    """Import and yield the case modules in `smoke/cases` (sorted by name)."""
    from . import cases as cases_pkg

    yield from cases_pkg.load()
