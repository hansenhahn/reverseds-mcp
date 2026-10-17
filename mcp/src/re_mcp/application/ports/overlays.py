"""Port for the cartridge overlay tables (y9/y7)."""
from typing import Protocol, runtime_checkable

from ...domain.overlays import Overlay, OverlayHit


@runtime_checkable
class Overlays(Protocol):
    """Port for the ROM overlay tables, per core (ARM9/ARM7)."""

    def overlay_list(self, core: str) -> list[Overlay]:
        """List the overlays of a core.

        Parameters:
            core (str): ``arm9`` or ``arm7``.

        Returns:
            list[Overlay]: The overlay entries.

        Raises:
            NdsRomError: If the core is unknown.
        """
        ...

    def overlay_for_address(self, addr: int, core: str = "arm9") -> OverlayHit | None:
        """Resolve a RAM address to the overlay that contains it.

        Parameters:
            addr (int): A RAM address.
            core (str): ``arm9`` or ``arm7``.

        Returns:
            OverlayHit | None: The overlay and the offset, or None.
        """
        ...
