"""Interpretação nativa das tabelas de overlay (y9/y7) do cartucho NDS.

Os overlays são descritos pelo header da ROM (`arm9_overlay`/`arm7_overlay`);
os dados de cada um ficam na FAT como arquivos comuns. Funções puras.
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


@dataclass(frozen=True, slots=True)
class OverlayHit:
    """Resolução de um endereço de RAM: o overlay e o deslocamento dentro dele."""

    overlay: Overlay
    offset: int


def parse_overlays(data: bytes, core: str) -> list[Overlay]:
    """Interpreta uma tabela de overlays (32 bytes por entrada).

    Parameters:
        data (bytes): Conteúdo da tabela (`arm9_overlay` ou `arm7_overlay`).
        core (str): ``arm9`` ou ``arm7``, para rotular as entradas.

    Returns:
        list[Overlay]: As entradas de overlay.
    """
    overlays: list[Overlay] = []
    for off in range(0, len(data) - (_ENTRY_SIZE - 1), _ENTRY_SIZE):
        index, ram, size, bss, _sinit, _sinit_end, file_id, _res = struct.unpack_from(
            "<8I", data, off
        )
        overlays.append(
            Overlay(
                core=core,
                index=index,
                ram_address=ram,
                ram_size=size,
                bss_size=bss,
                file_id=file_id,
            )
        )
    return overlays


def resolve_address(overlays: list[Overlay], addr: int) -> OverlayHit | None:
    """Resolve um endereço de RAM para o overlay que o contém.

    Parameters:
        overlays (list[Overlay]): As entradas (de um core).
        addr (int): Endereço de RAM.

    Returns:
        OverlayHit | None: O overlay e o deslocamento dentro dele, ou None.
    """
    for overlay in overlays:
        if overlay.ram_address <= addr < overlay.ram_address + overlay.ram_size:
            return OverlayHit(overlay=overlay, offset=addr - overlay.ram_address)
    return None
