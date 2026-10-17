"""Portas (interfaces) do domínio para os backends do emulador.

O domínio fala com estas abstrações; os adaptadores concretos (infra) as
implementam. Usa `typing.Protocol` (não ABCs); os contratos são verificados
estaticamente com `pyright` (ver `pyrightconfig.json`).
"""
from .cartfs import CartFs
from .control import ControlChannel
from .debug import Debugger
from .files import FileStore
from .overlays import Overlays

__all__ = ["CartFs", "ControlChannel", "Debugger", "FileStore", "Overlays"]
