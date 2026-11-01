"""Bridge: holds the backends (control channel, gdb, ROM) and the lifecycle.

Composition root: lazy wiring of the adapters and the domain objects. The connection
is only opened on the first call, so the MCP starts even without the emulator running.
"""
import logging
import threading

from .config import Config
from .application.ports import CartFs, ControlChannel, Debugger, FileStore, Overlays
from .application.decomp import DecompSnippets
from .application.snapshots import Snapshots
from .domain.cartfs import RomInfo
from .domain.io import IoMap
from .domain.symbols import Symbol, SymbolTable
from .infra.control import UnixControlChannel
from .infra.files import OutDir
from .infra.gdb import GdbBackend
from .infra.ndsrom import ChannelRom, NdsRomError

log = logging.getLogger("re_mcp.bridge")


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
        self._rom: ChannelRom | None = None
        self._symbols = SymbolTable([])
        self._symbols_loaded = False
        self._symbols_lock = threading.RLock()
        self._files: OutDir | None = None
        self._snapshots: Snapshots | None = None
        self._decomp: DecompSnippets | None = None
        self._io_map: IoMap | None = None

    @property
    def config(self) -> Config:
        """The configuration in use."""
        return self._config

    def symbols(self) -> SymbolTable:
        """The symbol table, loading ``symbols.json`` on first use."""
        with self._symbols_lock:
            if not self._symbols_loaded:
                self._symbols_loaded = True
                text = self.files().read_text("symbols.json")
                if text:
                    try:
                        self._symbols = SymbolTable.from_json(text)
                    except ValueError as exc:
                        log.warning("tabela de símbolos inválida; começando vazia: %s", exc)
                        self._symbols = SymbolTable([])
            return self._symbols

    def set_symbols(self, symbols: SymbolTable) -> None:
        """Replace the symbol table (not persisted until ``save_symbols``)."""
        with self._symbols_lock:
            self._symbols = symbols
            self._symbols_loaded = True

    def add_symbol(self, symbol: Symbol) -> str:
        """Add a symbol and persist the table, returning the JSON path."""
        with self._symbols_lock:
            self.symbols().add(symbol)
            return self.save_symbols()

    def save_symbols(self) -> str:
        """Persist the symbol table and return the JSON path."""
        with self._symbols_lock:
            return self.files().write_text("symbols.json", self.symbols().to_json())

    def decomp(self) -> DecompSnippets:
        """Return the decomp-snippet service."""
        if self._decomp is None:
            self._decomp = DecompSnippets(self.files())
        return self._decomp

    def snapshots(self) -> Snapshots:
        """Return the memory-snapshot service (`mem_snapshot`/`state_diff`)."""
        if self._snapshots is None:
            self._snapshots = Snapshots(self.debugger(), self.files())
        return self._snapshots

    def io_map(self) -> IoMap:
        """Return the IO register map (built on the first call, at the composition root).

        Returns:
            IoMap: The IO map.
        """
        if self._io_map is None:
            self._io_map = IoMap.default()
        return self._io_map

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

    def _rom_instance(self) -> ChannelRom:
        if self._rom is None:
            self._rom = ChannelRom(self.control())
        return self._rom

    def refresh_rom(self) -> RomInfo:
        """Reload the emulator ROM when it changed and fail when there is no cart.

        Returns:
            RomInfo: The loaded ROM identity.

        Raises:
            NdsRomError: If there is no ROM loaded in the emulator.
            ControlError: If the control channel fails.
        """
        return self._rom_instance().refresh()

    def rom_info(self) -> RomInfo:
        """Return the identity of the ROM loaded in the emulator.

        Returns:
            RomInfo: The loaded ROM identity (``loaded=False`` without a cart).

        Raises:
            ControlError: If the control channel fails.
        """
        return self._rom_instance().info()

    def cartfs(self) -> CartFs:
        """Return the ROM filesystem served by the emulator.

        Returns:
            CartFs: The ROM filesystem.

        Raises:
            NdsRomError: If there is no ROM loaded in the emulator.
            ControlError: If the control channel fails.
        """
        return self._rom_instance()

    def overlays(self) -> Overlays:
        """Return the ROM overlay tables served by the emulator.

        Returns:
            Overlays: The ROM overlay tables.

        Raises:
            NdsRomError: If there is no ROM loaded in the emulator.
            ControlError: If the control channel fails.
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
        self._rom = None
