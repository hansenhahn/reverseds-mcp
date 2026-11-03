"""Application service: keep a RAM patch set and reapply it on demand."""
import json
import logging
import threading

from ..domain.patch import Patch
from .ports import Debugger, FileStore

log = logging.getLogger("re_mcp")

_PATCH_FILE = "patches.json"


class PatchManager:
    """Service: persist and reapply one active RAM patch set."""

    def __init__(self, debugger: Debugger, files: FileStore) -> None:
        """Build the manager over the debugger and artifact store.

        Parameters:
            debugger (Debugger): Debug backend used to write RAM.
            files (FileStore): Artifact store for ``patches.json``.
        """
        self._debugger = debugger
        self._files = files
        self._lock = threading.RLock()
        self._patch: Patch | None = None
        self._loaded = False

    def _load(self) -> None:
        """Load ``patches.json`` once (invalid data is logged and ignored)."""
        if self._loaded:
            return
        self._loaded = True
        text = self._files.read_text(_PATCH_FILE)
        if not text:
            return
        try:
            patch = Patch.from_json(text)
        except ValueError as exc:
            log.warning("patches.json inválido; começando vazio: %s", exc)
            return
        self._patch = patch if patch.writes else None

    def _save(self) -> str:
        """Persist the active patch and return the artifact path."""
        patch = self._patch
        payload = json.dumps(
            {"writes": patch.to_specs() if patch is not None else []}, indent=2
        )
        return self._files.write_text(_PATCH_FILE, payload)

    def _write(self, patch: Patch) -> None:
        """Write every patch entry through the debugger."""
        for write in patch.writes:
            self._debugger.write_memory(write.addr, write.data)

    def set(
        self, specs: list[dict], persist: bool = True, apply: bool = True
    ) -> tuple[Patch, str | None]:
        """Replace the active patch, optionally applying and persisting it.

        Parameters:
            specs (list[dict]): ``[{addr, bytes}, ...]``.
            persist (bool): Write ``patches.json``.
            apply (bool): Write the bytes to RAM now.

        Returns:
            tuple[Patch, str | None]: The patch and the persisted path (or None).

        Raises:
            ValueError: If the patch spec is invalid.
            DebugError: If applying to RAM fails.
        """
        patch = Patch.from_specs(specs)
        with self._lock:
            if apply:
                self._write(patch)
            self._patch = patch
            path = self._save() if persist else None
            return patch, path

    def apply(self) -> int:
        """Reapply the active patch; return the number of writes (0 if none)."""
        with self._lock:
            self._load()
            if self._patch is None:
                return 0
            self._write(self._patch)
            return len(self._patch.writes)

    def clear(self, persist: bool = True) -> int:
        """Forget the active patch (without reverting bytes); return its size."""
        with self._lock:
            self._load()
            count = len(self._patch.writes) if self._patch is not None else 0
            self._patch = None
            if persist:
                self._save()
            return count

    def list(self) -> Patch | None:
        """Return the active patch, or None."""
        with self._lock:
            self._load()
            return self._patch
