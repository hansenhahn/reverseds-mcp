"""Depuração: alvos de watchpoint e diff de memória (domínio, sobre a porta Debugger)."""
import json
import os
from dataclasses import dataclass

from .ports import Debugger, FileStore

_CONTEXT_REGS = ("r0", "r1", "r2", "r3", "sp", "lr")
_SNAP_SUBDIR = "snapshots"


@dataclass(frozen=True, slots=True)
class WatchpointHit:
    """Parada de watchpoint: PC e contexto de registradores."""

    pc: int
    registers: dict[str, int]


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Um bloco de memória guardado, com seu endereço base."""

    addr: int
    data: bytes


@dataclass(frozen=True, slots=True)
class MemoryChange:
    """Um byte que mudou entre dois estados."""

    addr: int
    old: int
    new: int


@dataclass(frozen=True, slots=True)
class MemoryDiff:
    """Comparação de dois blocos de memória de mesmo tamanho."""

    changes: tuple[MemoryChange, ...]

    @classmethod
    def between(cls, before: bytes, after: bytes, base: int) -> "MemoryDiff":
        """Compara dois blocos e lista os bytes que mudaram.

        Parameters:
            before (bytes): Bloco anterior.
            after (bytes): Bloco atual.
            base (int): Endereço base do bloco.

        Returns:
            MemoryDiff: As mudanças ``(addr, old, new)``.
        """
        return cls(
            tuple(
                MemoryChange(base + offset, old, new)
                for offset, (old, new) in enumerate(zip(before, after))
                if old != new
            )
        )

    def __len__(self) -> int:
        return len(self.changes)


class Watchpoints:
    """Serviço: acha quem escreve/lê um endereço (watchpoint + execução)."""

    def __init__(self, debugger: Debugger) -> None:
        self._debugger = debugger

    def find_write(
        self, addr: int, timeout: float = 30.0, condition: str | None = None
    ) -> WatchpointHit | None:
        """Acha o código que escreve em ``addr`` (watchpoint de escrita + run)."""
        return self._find(addr, "write", timeout, condition)

    def find_read(
        self, addr: int, timeout: float = 30.0, condition: str | None = None
    ) -> WatchpointHit | None:
        """Acha o código que lê ``addr`` (watchpoint de leitura + run)."""
        return self._find(addr, "read", timeout, condition)

    def _find(
        self, addr: int, kind: str, timeout: float, condition: str | None
    ) -> WatchpointHit | None:
        number = self._debugger.set_watchpoint(addr, kind, condition)
        try:
            if not self._debugger.continue_(timeout):
                return None
            pc = self._debugger.read_register("pc")
            registers = {
                name: self._debugger.read_register(name) for name in _CONTEXT_REGS
            }
            return WatchpointHit(pc=pc, registers=registers)
        finally:
            self._debugger.remove(number)


class SnapshotError(RuntimeError):
    """Erro ao capturar ou comparar um snapshot de memória."""


class Snapshots:
    """Serviço: captura blocos de memória e compara com o estado atual.

    Persiste cada captura no diretório de saída (porta ``FileStore``) e mantém um
    cache em memória para comparações rápidas.
    """

    def __init__(self, debugger: Debugger, store: FileStore) -> None:
        """Monta o serviço.

        Parameters:
            debugger (Debugger): Backend de debug (leitura de memória).
            store (FileStore): Onde persistir as capturas.
        """
        self._debugger = debugger
        self._store = store
        self._cache: dict[str, Snapshot] = {}

    def capture(self, name: str, addr: int, size: int) -> Snapshot:
        """Lê ``size`` bytes de ``addr``, guarda e persiste sob ``name``.

        Parameters:
            name (str): Nome da captura (sanitizado).
            addr (int): Endereço base.
            size (int): Tamanho em bytes.

        Returns:
            Snapshot: A captura guardada.
        """
        data = self._debugger.read_memory(addr, size)
        snapshot = Snapshot(addr, data)
        safe = os.path.basename(name) or "snapshot"
        self._cache[safe] = snapshot
        self._store.write_bytes(f"{_SNAP_SUBDIR}/{safe}.bin", data)
        self._store.write_text(
            f"{_SNAP_SUBDIR}/{safe}.json",
            json.dumps({"addr": addr, "size": len(data)}),
        )
        return snapshot

    def diff(self, name: str) -> MemoryDiff:
        """Compara a memória atual com a captura ``name``.

        Parameters:
            name (str): Nome da captura.

        Returns:
            MemoryDiff: As mudanças observadas.

        Raises:
            SnapshotError: Se a captura não existir (nem em memória, nem em disco).
        """
        safe = os.path.basename(name)
        snapshot = self._cache.get(safe) or self._load(safe)
        if snapshot is None:
            raise SnapshotError(f"captura '{name}' não existe")
        after = self._debugger.read_memory(snapshot.addr, len(snapshot.data))
        return MemoryDiff.between(snapshot.data, after, snapshot.addr)

    def _load(self, name: str) -> Snapshot | None:
        data = self._store.read_bytes(f"{_SNAP_SUBDIR}/{name}.bin")
        meta = self._store.read_text(f"{_SNAP_SUBDIR}/{name}.json")
        if data is None or meta is None:
            return None
        snapshot = Snapshot(int(json.loads(meta)["addr"]), data)
        self._cache[name] = snapshot
        return snapshot
