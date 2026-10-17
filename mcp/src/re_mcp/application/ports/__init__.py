"""Application ports (interfaces) for the emulator backends.

The application layer talks to these abstractions; the concrete adapters (infra)
implement them. Uses `typing.Protocol` (not ABCs); the contracts are checked
statically with `pyright` (see `pyrightconfig.json`).
"""
from .cartfs import CartFs
from .control import ControlChannel
from .debug import Debugger
from .files import FileStore
from .overlays import Overlays

__all__ = ["CartFs", "ControlChannel", "Debugger", "FileStore", "Overlays"]
