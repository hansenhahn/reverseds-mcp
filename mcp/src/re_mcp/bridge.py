"""Bridge: holds the backends (control channel, gdb, ROM) and the lifecycle.

Composition root: lazy wiring of the adapters and the domain objects. The connection
is only opened on the first call, so the MCP starts even without the emulator running.
"""
from .config import Config
from .application.ports import CartFs, ControlChannel, Debugger, FileStore, Overlays
from .application.snapshots import Snapshots
from .domain.symbols import SymbolTable
from .infra.control import UnixControlChannel
from .infra.files import OutDir
from .infra.gdb import GdbBackend
from .infra.ndsrom import NdsRom, NdsRomError


class Bridge:
    """Lazy access to the emulator backends and the domain objects."""

    def __init__(self, config: Config) -> None:
        """Store the configuration.

        Parameters:
            config (Config): Backend configuration.
        """
        self._config = config
        self._control: ControlChannel | None = None
        self._debugger: Debugger | None = None
        self._rom: NdsRom | None = None
        self._symbols = SymbolTable([])
        self._files: OutDir | None = None
        self._snapshots: Snapshots | None = None

    @property
    def config(self) -> Config:
        """The configuration in use."""
        return self._config

    def symbols(self) -> SymbolTable:
        """The loaded symbol table (via `symbol_load`)."""
        return self._symbols

    def set_symbols(self, symbols: SymbolTable) -> None:
        """Replace the symbol table.

        Parameters:
            symbols (SymbolTable): The new table.
        """
        self._symbols = symbols

    def snapshots(self) -> Snapshots:
        """Return the memory-snapshot service (`mem_snapshot`/`state_diff`)."""
        if self._snapshots is None:
            self._snapshots = Snapshots(self.debugger(), self.files())
        return self._snapshots

    def files(self) -> FileStore:
        """Return the artifact storage (output directory).

        Returns:
            FileStore: The output storage (`RE_MCP_OUT_DIR`).
        """
        if self._files is None:
            self._files = OutDir(self._config.out_dir)
        return self._files

    def control(self) -> ControlChannel:
        """Return the control channel, opening it on the first call.

        Returns:
            ControlChannel: The connected channel.

        Raises:
            ControlError: If it cannot connect.
        """
        if self._control is None:
            self._control = UnixControlChannel(self._config.control_socket)
        return self._control

    def debugger(self) -> Debugger:
        """Return the debug backend, creating it on the first call.

        Returns:
            Debugger: The backend (gdb), not connected yet.
        """
        if self._debugger is None:
            self._debugger = GdbBackend(
                self._config.gdb_path,
                self._config.arm9_port,
                self._config.arm7_port,
            )
        return self._debugger

    def _rom_instance(self) -> NdsRom:
        if self._rom is None:
            if not self._config.rom_path:
                raise NdsRomError("ROM não configurada (defina RE_MCP_ROM)")
            self._rom = NdsRom(self._config.rom_path)
        return self._rom

    def cartfs(self) -> CartFs:
        """Return the ROM filesystem, opening it on the first call.

        Returns:
            CartFs: The ROM filesystem.

        Raises:
            NdsRomError: If the ROM is not configured or cannot be parsed.
        """
        return self._rom_instance()

    def overlays(self) -> Overlays:
        """Return the ROM overlay parsing, opening it on the first call.

        Returns:
            Overlays: The ROM overlay tables.

        Raises:
            NdsRomError: If the ROM is not configured or cannot be parsed.
        """
        return self._rom_instance()

    def close(self) -> None:
        """Close the open backends."""
        if self._control is not None:
            self._control.close()
            self._control = None
        if self._debugger is not None:
            self._debugger.close()
            self._debugger = None
        if self._rom is not None:
            self._rom.close()
            self._rom = None
