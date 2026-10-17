"""Porta das tabelas de overlay (y9/y7) do cartucho."""
from typing import Protocol, runtime_checkable

from ...domain.overlays import Overlay, OverlayHit


@runtime_checkable
class Overlays(Protocol):
    """Porta para as tabelas de overlay da ROM, por core (ARM9/ARM7)."""

    def overlay_list(self, core: str) -> list[Overlay]:
        """Lista os overlays de um core.

        Parameters:
            core (str): ``arm9`` ou ``arm7``.

        Returns:
            list[Overlay]: As entradas de overlay.

        Raises:
            NdsRomError: Se o core for desconhecido.
        """
        ...

    def overlay_for_address(self, addr: int, core: str = "arm9") -> OverlayHit | None:
        """Resolve um endereço de RAM para o overlay que o contém.

        Parameters:
            addr (int): Endereço de RAM.
            core (str): ``arm9`` ou ``arm7``.

        Returns:
            OverlayHit | None: O overlay e o deslocamento, ou None.
        """
        ...
