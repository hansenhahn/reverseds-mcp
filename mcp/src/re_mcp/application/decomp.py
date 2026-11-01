"""Application service: persist decomp snippets (C+ASM) by address."""
import json
import threading

from ..domain.decomp import DecompSnippet
from .ports import FileStore

_FILE = "decomp.json"


class DecompSnippets:
    """Service: load, query and store decomp snippets in the output directory."""

    def __init__(self, store: FileStore) -> None:
        """Build the service.

        Parameters:
            store (FileStore): Artifact storage (output directory).
        """
        self._store = store
        self._lock = threading.RLock()
        self._items: dict[int, DecompSnippet] | None = None

    def _load(self) -> None:
        if self._items is not None:
            return
        self._items = {}
        text = self._store.read_text(_FILE)
        if not text:
            return
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return
        if not isinstance(data, dict):
            return
        for key, value in data.items():
            if not isinstance(value, dict):
                continue
            try:
                addr = int(key, 16)
            except (TypeError, ValueError):
                continue
            self._items[addr] = DecompSnippet(
                addr=addr,
                c=value.get("c"),
                asm=value.get("asm"),
            )

    def get(self, addr: int) -> DecompSnippet | None:
        """Return the snippet at ``addr``, if any."""
        with self._lock:
            self._load()
            assert self._items is not None
            return self._items.get(addr)

    def put(self, addr: int, c: str | None, asm: str | None) -> DecompSnippet:
        """Store/merge a snippet at ``addr`` and persist it."""
        with self._lock:
            self._load()
            assert self._items is not None
            current = self._items.get(addr)
            snippet = DecompSnippet(
                addr=addr,
                c=c if c is not None else (current.c if current else None),
                asm=asm if asm is not None else (current.asm if current else None),
            )
            self._items[addr] = snippet
            self._save()
            return snippet

    def _save(self) -> None:
        assert self._items is not None
        data = {
            f"0x{addr:08x}": {"c": snippet.c, "asm": snippet.asm}
            for addr, snippet in sorted(self._items.items())
        }
        self._store.write_text(_FILE, json.dumps(data, indent=2))
