"""Artifact storage in the MCP output directory (`RE_MCP_OUT_DIR`)."""
import os


class OutDir:
    """Implements the ``FileStore`` port by writing under the output directory."""

    def __init__(self, root: str) -> None:
        """Store the output root directory.

        Parameters:
            root (str): Output directory (`RE_MCP_OUT_DIR`).
        """
        self._root = os.path.abspath(root)

    def _path(self, name: str) -> str:
        full = os.path.abspath(os.path.join(self._root, name))
        if full != self._root and not full.startswith(self._root + os.sep):
            raise ValueError(f"nome fora do diretório de saída: {name!r}")
        return full

    def write_bytes(self, name: str, data: bytes) -> str:
        path = self._path(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def write_text(self, name: str, text: str) -> str:
        path = self._path(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def read_bytes(self, name: str) -> bytes | None:
        path = self._path(name)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as handle:
            return handle.read()

    def read_text(self, name: str) -> str | None:
        path = self._path(name)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as handle:
            return handle.read()
