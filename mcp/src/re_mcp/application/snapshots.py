"""Serviço de aplicação: captura e compara blocos de memória (Debugger + FileStore)."""
import json
import os

from ..domain.debug import MemoryDiff, Snapshot
from .ports import Debugger, FileStore

_SNAP_SUBDIR = "snapshots"


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
