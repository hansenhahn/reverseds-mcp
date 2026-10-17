"""Tabelas de overlay (y9/y7) do cartucho: entidades e agregado, sem I/O.

Os overlays são descritos pelo header da ROM (`arm9_overlay`/`arm7_overlay`);
os dados de cada um ficam na FAT como arquivos comuns.
"""
import struct
from dataclasses import dataclass

_ENTRY_SIZE = 32


@dataclass(frozen=True, slots=True)
class Overlay:
    """Uma entrada de overlay: onde carrega na RAM e qual arquivo traz os dados."""

    core: str
    index: int
    ram_address: int
    ram_size: int
    bss_size: int
    file_id: int

    def covers(self, addr: int) -> bool:
        """Se ``addr`` cai na RAM ocupada por este overlay.

        Parameters:
            addr (int): Endereço de RAM.

        Returns:
            bool: True se ``ram_address <= addr < ram_address + ram_size``.
        """
        return self.ram_address <= addr < self.ram_address + self.ram_size


@dataclass(frozen=True, slots=True)
class OverlayHit:
    """Resolução de um endereço de RAM: o overlay e o deslocamento dentro dele."""

    overlay: Overlay
    offset: int


class OverlayTable:
    """Agregado: as entradas de overlay de um core (ARM9/ARM7)."""

    def __init__(self, overlays: list[Overlay]) -> None:
        self._overlays = overlays

    @classmethod
    def from_bytes(cls, data: bytes, core: str) -> "OverlayTable":
        """Interpreta uma tabela de overlays (32 bytes por entrada).

        Parameters:
            data (bytes): Conteúdo da tabela (`arm9_overlay` ou `arm7_overlay`).
            core (str): ``arm9`` ou ``arm7``, para rotular as entradas.

        Returns:
            OverlayTable: As entradas de overlay.
        """
        overlays: list[Overlay] = []
        for off in range(0, len(data) - (_ENTRY_SIZE - 1), _ENTRY_SIZE):
            idx, ram, size, bss, _si, _sie, file_id, _res = struct.unpack_from(
                "<8I", data, off
            )
            overlays.append(
                Overlay(
                    core=core,
                    index=idx,
                    ram_address=ram,
                    ram_size=size,
                    bss_size=bss,
                    file_id=file_id,
                )
            )
        return cls(overlays)

    def entries(self) -> list[Overlay]:
        """As entradas de overlay."""
        return list(self._overlays)

    def for_address(self, addr: int) -> OverlayHit | None:
        """Resolve um endereço de RAM para o overlay que o contém.

        Parameters:
            addr (int): Endereço de RAM.

        Returns:
            OverlayHit | None: O overlay e o deslocamento, ou None.
        """
        for overlay in self._overlays:
            if overlay.covers(addr):
                return OverlayHit(overlay, addr - overlay.ram_address)
        return None
