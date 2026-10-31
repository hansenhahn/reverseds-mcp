"""Port for the debug backend (gdb connected to the melonDS stub)."""
from typing import Protocol, runtime_checkable

from ...domain.debug import Breakpoint, StackFrame


@runtime_checkable
class Debugger(Protocol):
    """Port for the debug backend (gdb connected to the melonDS stub)."""

    def connect(self, core: str) -> None:
        """Connect to the chosen core (``arm9`` or ``arm7``).

        Parameters:
            core (str): Target core.
        """
        ...

    def core(self) -> str | None:
        """Return the connected core (``arm9``/``arm7``), if any."""
        ...

    def watchpoint_limit(self) -> int:
        """Return the configured hardware watchpoint limit.

        Returns:
            int: The number of hardware watchpoint slots.
        """
        ...

    def refresh_registers(self) -> None:
        """Flush any client-side register cache so the next read hits the target."""
        ...

    def read_register(self, name: str) -> int:
        """Read a register by name (e.g. ``pc``).

        Parameters:
            name (str): Register name.

        Returns:
            int: The register value.
        """
        ...

    def write_register(self, name: str, value: int) -> None:
        """Write a value to a register.

        Parameters:
            name (str): Register name.
            value (int): Value to write.
        """
        ...

    def read_memory(self, addr: int, size: int) -> bytes:
        """Read ``size`` bytes of emulated memory at ``addr``.

        Parameters:
            addr (int): Address.
            size (int): Number of bytes.

        Returns:
            bytes: The bytes read.
        """
        ...

    def write_memory(self, addr: int, data: bytes) -> None:
        """Write ``data`` to emulated memory starting at ``addr``.

        Parameters:
            addr (int): Address.
            data (bytes): Bytes to write.
        """
        ...

    def set_watchpoint(self, addr: int, kind: str, condition: str | None = None) -> int:
        """Create a hardware watchpoint (``write``, ``read`` or ``access``).

        Parameters:
            addr (int): Watched address.
            kind (str): Access kind.
            condition (str | None): Optional gdb expression; gdb only stops when it
                is true (filters by value).

        Returns:
            int: The watchpoint number.
        """
        ...

    def set_breakpoint(
        self,
        addr: int,
        condition: str | None = None,
        commands: list[str] | None = None,
    ) -> int:
        """Create a code breakpoint at the address.

        Parameters:
            addr (int): Address.
            condition (str | None): Optional gdb expression; gdb only stops when true.
            commands (list[str] | None): Optional gdb commands run on the hit (one per line).

        Returns:
            int: The breakpoint number.
        """
        ...

    def remove(self, number: int) -> None:
        """Remove a breakpoint/watchpoint by number.

        Parameters:
            number (int): The breakpoint/watchpoint number.
        """
        ...

    def backtrace(self) -> list[StackFrame]:
        """Return the call stack of the connected core (innermost frame first).

        Returns:
            list[StackFrame]: The frames.
        """
        ...

    def breakpoints(self) -> list[Breakpoint]:
        """Return the active breakpoints/watchpoints known to the stub.

        Returns:
            list[Breakpoint]: The breakpoints/watchpoints.
        """
        ...

    def continue_(self, timeout: float = 30.0) -> bool:
        """Resume execution and wait for the stop.

        Parameters:
            timeout (float): Maximum wait time in seconds.

        Returns:
            bool: True if it stopped (breakpoint/watchpoint); False on timeout.
        """
        ...

    def step(self) -> None:
        """Execute one instruction."""
        ...

    def interrupt(self) -> None:
        """Interrupt execution."""
        ...

    def resume(self) -> None:
        """Resume execution in the background (non-blocking)."""
        ...

    def wait_stop(self, timeout: float) -> bool:
        """Wait for the background ``continue`` to stop.

        Parameters:
            timeout (float): Maximum wait time in seconds.

        Returns:
            bool: True if it stopped; False if still running.
        """
        ...

    def is_running(self) -> bool:
        """True if the target is executing (background continue active)."""
        ...

    def disconnect(self) -> None:
        """Disconnect from the target — the emulator runs again."""
        ...

    def close(self) -> None:
        """Shut down the debug backend."""
        ...
