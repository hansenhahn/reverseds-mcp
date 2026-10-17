"""NitroFS via `ndstool`: mapeia offsets da ROM em arquivos.

Em vez de reimplementar o parsing da FNT/FAT, delega ao `ndstool` (`-l`), que
lista ``<id> 0x<start> 0x<end> <size> <path>`` por arquivo. Assim não reinventamos
o formato (conforme as diretrizes).
"""
import os
import re
import subprocess

from ..domain.ports import CartFs

_LINE = re.compile(
    r"^\s*\d+\s+0x([0-9A-Fa-f]+)\s+0x([0-9A-Fa-f]+)\s+\d+\s+(/\S.*?)\s*$"
)


class NitroFsError(RuntimeError):
    """Erro ao listar o NitroFS da ROM."""


class NitroFs(CartFs):
    """Mapa offset→arquivo de uma ROM de NDS, obtido do `ndstool`."""

    def __init__(self, rom_path: str, ndstool_path: str = "ndstool") -> None:
        """Lista o filesystem da ROM com o `ndstool`.

        Parameters:
            rom_path (str): Caminho da ROM.
            ndstool_path (str): Executável do ndstool.

        Raises:
            NitroFsError: Se o ndstool falhar.
        """
        try:
            result = subprocess.run(
                [ndstool_path, "-l", rom_path],
                capture_output=True,
                text=True,
                env={**os.environ, "LC_ALL": "C"},
                check=False,
            )
        except OSError as exc:
            raise NitroFsError(f"não executou {ndstool_path}: {exc}") from exc
        if result.returncode != 0:
            raise NitroFsError(f"ndstool falhou: {result.stderr.strip()}")
        self._entries: list[tuple[int, int, str]] = []
        for line in result.stdout.splitlines():
            match = _LINE.match(line)
            if match:
                start = int(match.group(1), 16)
                end = int(match.group(2), 16)
                self._entries.append((start, end, match.group(3)))

    def file_count(self) -> int:
        """O número de arquivos listados."""
        return len(self._entries)

    def file_for_offset(self, offset: int) -> str | None:
        """Devolve o arquivo que contém ``offset`` (ou None).

        Parameters:
            offset (int): Offset na ROM.

        Returns:
            str | None: O caminho do arquivo, ou None.
        """
        for start, end, path in self._entries:
            if start <= offset < end:
                return path
        return None
