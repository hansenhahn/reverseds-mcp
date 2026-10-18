"""Case registry: each module exposes ``NAME`` and ``async def run(ctx)``."""
from __future__ import annotations

import importlib
import pkgutil
from typing import Awaitable, Callable

from ..harness import Ctx

Case = tuple[str, Callable[[Ctx], Awaitable[None]]]


def load() -> list[Case]:
    """Import every case module (sorted by file name) and return (name, run)."""
    cases: list[Case] = []
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        cases.append((module.NAME, module.run))
    return cases
