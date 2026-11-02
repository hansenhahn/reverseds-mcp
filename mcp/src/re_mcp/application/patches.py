"""Application service: compare two patches over the current memory."""
from ..domain.patch import Patch, PatchDiff
from .ports import Debugger


class PatchComparer:
    """Service: read the touched memory and diff the two patch results."""

    def __init__(self, debugger: Debugger) -> None:
        """Build the service."""
        self._debugger = debugger

    def compare(
        self, asm_specs: list[dict], c_specs: list[dict]
    ) -> tuple[Patch, Patch, PatchDiff]:
        """Return ``(asm, c_equiv, diff)`` for the current memory."""
        asm = Patch.from_specs(asm_specs)
        c_equiv = Patch.from_specs(c_specs)
        memory: dict[int, int] = {}
        for start, end in Patch.merged_regions(asm, c_equiv):
            data = self._debugger.read_memory(start, end - start)
            for offset, byte in enumerate(data):
                memory[start + offset] = byte
        return asm, c_equiv, PatchDiff.between(asm, c_equiv, memory)
