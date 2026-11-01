"""Application service: backtrace with a stack-scan fallback."""
from ..domain.backtrace import StackScanner
from ..domain.debug import StackFrame
from ..domain.disasm import Disassembler
from .ports import Debugger

_STACK_DEPTH = 0x800
_MIN_FRAMES = 4
_MAX_CANDIDATES = 32


class Backtrace:
    """Service: use gdb frames, falling back to a stack scan when they are short."""

    def __init__(
        self,
        debugger: Debugger,
        depth: int = _STACK_DEPTH,
        min_frames: int = _MIN_FRAMES,
        limit: int = _MAX_CANDIDATES,
    ) -> None:
        """Build the service.

        Parameters:
            debugger (Debugger): The stopped debug backend.
            depth (int): Bytes of stack to scan.
            min_frames (int): Minimum gdb frames before skipping the stack scan.
            limit (int): Maximum stack candidates to append.
        """
        self._debugger = debugger
        self._depth = depth
        self._min_frames = min_frames
        self._limit = limit
        self._disassembler = Disassembler()

    def _is_return_address(self, addr: int) -> bool:
        """Whether the bytes before ``addr`` contain a BL/BLX that returns there."""
        if addr < 4:
            return False
        try:
            code = self._debugger.read_memory(addr - 4, 4)
        except RuntimeError:
            return False
        for mode in ("arm", "thumb"):
            for insn in self._disassembler.disassemble(code, addr - 4, mode):
                if insn.mnemonic.startswith("bl") and insn.address + insn.size == addr:
                    return True
        return False

    def frames(self) -> list[StackFrame]:
        """Return the call stack, appending stack candidates when needed."""
        frames = list(self._debugger.backtrace())
        if len(frames) >= self._min_frames:
            return frames
        try:
            pc = self._debugger.read_register("pc")
            sp = self._debugger.read_register("sp")
            stack = self._debugger.read_memory(sp, self._depth)
        except RuntimeError:
            return frames
        scanner = StackScanner(
            exclude={pc, *(frame.pc for frame in frames)},
            exclude_range=(sp, sp + len(stack)),
            limit=self._limit,
        )
        for addr in scanner.scan(stack):
            if not self._is_return_address(addr):
                continue
            frames.append(
                StackFrame(index=len(frames), pc=addr, function=None, source="stack")
            )
        return frames
