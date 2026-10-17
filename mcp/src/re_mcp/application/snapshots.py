"""Application service: capture and compare memory blocks (Debugger + FileStore)."""
import json
import os

from ..domain.debug import MemoryDiff, Snapshot
from .ports import Debugger, FileStore

_SNAP_SUBDIR = "snapshots"


class SnapshotError(RuntimeError):
    """Error capturing or comparing a memory snapshot."""


class Snapshots:
    """Service: capture memory blocks and compare with the current state.

    Persists each capture in the output directory (``FileStore`` port) and keeps an
    in-memory cache for fast comparisons.
    """

    def __init__(self, debugger: Debugger, store: FileStore) -> None:
        """Build the service.

        Parameters:
            debugger (Debugger): Debug backend (memory reads).
            store (FileStore): Where to persist the captures.
        """
        self._debugger = debugger
        self._store = store
        self._cache: dict[str, Snapshot] = {}

    def capture(self, name: str, addr: int, size: int) -> Snapshot:
        """Read ``size`` bytes at ``addr``, store and persist under ``name``.

        Parameters:
            name (str): Capture name (sanitized).
            addr (int): Base address.
            size (int): Size in bytes.

        Returns:
            Snapshot: The stored capture.
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
        """Compare the current memory with the capture ``name``.

        Parameters:
            name (str): The capture name.

        Returns:
            MemoryDiff: The observed changes.

        Raises:
            SnapshotError: If the capture does not exist (neither in memory nor on disk).
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
