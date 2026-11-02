"""Application service: overlay resolution with candidates and active selection."""
import threading
from dataclasses import dataclass

from ..domain.overlays import OverlayDetails, OverlayHit
from .ports import Overlays


@dataclass(frozen=True, slots=True)
class OverlayResolution:
    """Result of resolving an address against the overlay table."""

    candidates: tuple[OverlayHit, ...]
    selected: OverlayHit | None
    ambiguous: bool
    code_base: int | None
    prefix_size: int | None


class OverlayResolver:
    """Service: resolve overlay candidates and remember the active selection."""

    def __init__(self, overlays: Overlays) -> None:
        """Build the resolver over the overlay port.

        Parameters:
            overlays (Overlays): The overlay table adapter.
        """
        self._overlays = overlays
        self._lock = threading.RLock()
        self._selection: dict[str, tuple[int, int | None]] = {}

    def select(
        self, index: int | None, core: str = "arm9", code_base: int | None = None
    ) -> OverlayDetails | None:
        """Select/clear the overlay considered resident for ``core``.

        Parameters:
            index (int | None): Overlay ID, or ``None`` to clear.
            core (str): ``arm9`` or ``arm7``.
            code_base (int | None): Optional address where the overlay code starts.

        Returns:
            OverlayDetails | None: The selected details, or None when clearing.

        Raises:
            NdsRomError: If the overlay does not exist.
            ValueError: If ``code_base`` is outside the overlay's RAM range.
        """
        with self._lock:
            if index is None:
                self._selection.pop(core, None)
                return None
            details = self._overlays.overlay_details(index, core)
            details = details.with_code_base(code_base)
            self._selection[core] = (index, code_base)
            return details

    def clear(self, core: str = "arm9") -> None:
        """Clear the active overlay for ``core``."""
        with self._lock:
            self._selection.pop(core, None)

    def selection(self, core: str = "arm9") -> tuple[int | None, int | None]:
        """Return ``(overlay_id, code_base)`` for ``core`` (``(None, None)`` if none)."""
        with self._lock:
            return self._selection.get(core, (None, None))

    def details(
        self, index: int, core: str = "arm9", code_base: int | None = None
    ) -> OverlayDetails:
        """Return overlay details, applying the active/explicit code base.

        Parameters:
            index (int): Overlay ID.
            core (str): ``arm9`` or ``arm7``.
            code_base (int | None): Optional explicit code base.

        Returns:
            OverlayDetails: The details with optional ``code_base``/``prefix_size``.
        """
        selected_index, selected_code = self.selection(core)
        chosen_code = (
            code_base
            if code_base is not None
            else selected_code if selected_index == index else None
        )
        return self._overlays.overlay_details(index, core).with_code_base(chosen_code)

    def resolve(
        self,
        addr: int,
        core: str = "arm9",
        overlay: int | None = None,
        code_base: int | None = None,
    ) -> OverlayResolution:
        """Resolve ``addr`` into all candidates plus an optional selected hit.

        Parameters:
            addr (int): RAM address.
            core (str): ``arm9`` or ``arm7``.
            overlay (int | None): Explicit overlay ID (overrides the active one).
            code_base (int | None): Explicit code base (overrides the active one).

        Returns:
            OverlayResolution: Candidates, selected hit, ambiguity and offsets.
        """
        raw_hits = tuple(self._overlays.overlay_candidates(addr, core))
        selected_index, selected_code = self.selection(core)
        chosen_index = overlay if overlay is not None else selected_index
        if code_base is not None:
            chosen_code = code_base
        elif overlay is None or overlay == selected_index:
            chosen_code = selected_code
        else:
            chosen_code = None

        selected_raw: OverlayHit | None = None
        if chosen_index is not None:
            selected_raw = next(
                (hit for hit in raw_hits if hit.overlay.index == chosen_index), None
            )
        elif len(raw_hits) == 1:
            selected_raw = raw_hits[0]

        if chosen_code is not None:
            if selected_raw is not None:
                valid = (
                    selected_raw.overlay.ram_address <= chosen_code
                    < selected_raw.overlay.ram_address + selected_raw.overlay.ram_size
                )
                if not valid:
                    raise ValueError("code_base fora do intervalo da overlay")
            elif raw_hits:
                valid = any(
                    hit.overlay.ram_address <= chosen_code
                    < hit.overlay.ram_address + hit.overlay.ram_size
                    for hit in raw_hits
                )
                if not valid:
                    raise ValueError("code_base fora do intervalo da overlay")
            hits = tuple(
                OverlayHit(
                    hit.overlay,
                    hit.offset_file,
                    addr - chosen_code
                    if hit.overlay.ram_address <= chosen_code
                    < hit.overlay.ram_address + hit.overlay.ram_size
                    else None,
                )
                for hit in raw_hits
            )
        else:
            hits = raw_hits

        selected: OverlayHit | None = None
        if chosen_index is not None:
            selected = next(
                (hit for hit in hits if hit.overlay.index == chosen_index), None
            )
        elif len(hits) == 1:
            selected = hits[0]

        prefix_size = (
            chosen_code - selected.overlay.ram_address
            if chosen_code is not None and selected is not None
            else None
        )
        return OverlayResolution(
            candidates=hits,
            selected=selected,
            ambiguous=len(hits) > 1,
            code_base=chosen_code,
            prefix_size=prefix_size,
        )
