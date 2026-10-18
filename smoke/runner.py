"""Smoke runner: boots melonDS once and runs every case against the real MCP.

Usage:
    uv run --project mcp python -m smoke --rom /path/to/game.nds [--only gdb]

Each case opens a fresh MCP stdio session, so failures are isolated. The exit
code is non-zero when any case fails (suitable for a local pre-push hook).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

from .cases import Case, load
from .harness import DEFAULT_MELONDS, DEFAULT_SOCKET, Ctx, Emulator


def _describe(exc: BaseException) -> str:
    """Flatten an exception (including exception groups) into one message."""
    if isinstance(exc, BaseExceptionGroup):
        return " | ".join(_describe(inner) for inner in exc.exceptions)
    return f"{type(exc).__name__}: {exc}"


async def _run_all(
    ctx: Ctx, only: str | None, traceback: bool
) -> list[tuple[str, bool, str, float]]:
    results: list[tuple[str, bool, str, float]] = []
    for name, run in load():
        if only and only not in name:
            continue
        started = time.monotonic()
        try:
            await run(ctx)
            results.append((name, True, "", time.monotonic() - started))
        except Exception as exc:  # noqa: BLE001 - report any case failure
            detail = _describe(exc)
            if traceback:
                import traceback as tb

                detail = tb.format_exc()
            results.append((name, False, detail, time.monotonic() - started))
    return results


def main() -> int:
    """Parse args, boot the emulator, run the cases and report."""
    parser = argparse.ArgumentParser(prog="smoke")
    parser.add_argument("--rom", default=os.environ.get("RE_MCP_ROM") or os.environ.get("SMOKE_ROM"))
    parser.add_argument("--socket", default=DEFAULT_SOCKET)
    parser.add_argument("--melonds", default=os.environ.get("MELONDS_BIN", str(DEFAULT_MELONDS)))
    parser.add_argument("--out", default=None, help="output dir for captures (default: temp)")
    parser.add_argument("--only", default=None, help="run only cases whose name contains this")
    parser.add_argument("--keep", action="store_true", help="leave the emulator running")
    parser.add_argument("--traceback", action="store_true", help="print full tracebacks")
    args = parser.parse_args()

    if not args.rom:
        print("defina --rom (ou RE_MCP_ROM / SMOKE_ROM)", file=sys.stderr)
        return 2
    rom = Path(args.rom).expanduser()
    melonds = Path(args.melonds).expanduser()
    if not rom.exists():
        print(f"ROM não encontrada: {rom}", file=sys.stderr)
        return 2
    if not melonds.exists():
        print(f"melonDS não encontrado: {melonds} (defina MELONDS_BIN)", file=sys.stderr)
        return 2

    out_dir = Path(args.out).expanduser() if args.out else Path(tempfile.mkdtemp(prefix="smoke-out-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    log = Path(tempfile.gettempdir()) / "smoke-melonds.log"

    emulator = Emulator(rom=rom, socket=args.socket, binary=melonds, log=log)
    print(f">> melonDS headless: {melonds}")
    print(f">> socket: {args.socket}")
    try:
        emulator.start()
    except Exception as exc:  # noqa: BLE001
        print(f"!! falha ao subir o emulador: {exc}", file=sys.stderr)
        return 2

    ctx = Ctx(rom=rom, socket=args.socket, out_dir=out_dir)
    try:
        results = asyncio.run(_run_all(ctx, args.only, args.traceback))
    finally:
        if not args.keep:
            emulator.stop()

    print()
    failed = 0
    for name, ok, detail, elapsed in results:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}  ({elapsed:.1f}s)")
        if not ok:
            print(f"       {detail}")
            failed += 1
    print()
    print(f"{len(results) - failed}/{len(results)} casos OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
