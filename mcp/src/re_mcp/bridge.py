"""Ponte: mantém os backends (canal de controle, gdb, ROM) e o ciclo de vida.

Composition root: fiação lazy dos adaptadores e dos objetos de domínio. A conexão
só é aberta na primeira chamada, para o MCP subir mesmo sem emulador rodando.
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
    """Acesso lazy aos backends do emulador e aos objetos de domínio."""

    def __init__(self, config: Config) -> None:
        """Guarda a configuração.

        Parameters:
            config (Config): Configuração dos backends.
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
        """A configuração em uso."""
        return self._config

    def symbols(self) -> SymbolTable:
        """A tabela de símbolos carregada (via `symbol_load`)."""
        return self._symbols

    def set_symbols(self, symbols: SymbolTable) -> None:
        """Substitui a tabela de símbolos.

        Parameters:
            symbols (SymbolTable): A nova tabela.
        """
        self._symbols = symbols

    def snapshots(self) -> Snapshots:
        """Devolve o serviço de capturas de memória (`mem_snapshot`/`state_diff`)."""
        if self._snapshots is None:
            self._snapshots = Snapshots(self.debugger(), self.files())
        return self._snapshots

    def files(self) -> FileStore:
        """Devolve o armazenamento de artefatos (diretório de saída).

        Returns:
            FileStore: O armazenamento de saída (`RE_MCP_OUT_DIR`).
        """
        if self._files is None:
            self._files = OutDir(self._config.out_dir)
        return self._files

    def control(self) -> ControlChannel:
        """Devolve o canal de controle, abrindo-o na primeira chamada.

        Returns:
            ControlChannel: O canal conectado.

        Raises:
            ControlError: Se não for possível conectar.
        """
        if self._control is None:
            self._control = UnixControlChannel(self._config.control_socket)
        return self._control

    def debugger(self) -> Debugger:
        """Devolve o backend de debug, criando-o na primeira chamada.

        Returns:
            Debugger: O backend (gdb), ainda não conectado.
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
        """Devolve o filesystem da ROM, abrindo-a na primeira chamada.

        Returns:
            CartFs: O filesystem da ROM.

        Raises:
            NdsRomError: Se a ROM não estiver configurada ou não puder ser interpretada.
        """
        return self._rom_instance()

    def overlays(self) -> Overlays:
        """Devolve a interpretação de overlays da ROM, abrindo-a na primeira chamada.

        Returns:
            Overlays: As tabelas de overlay da ROM.

        Raises:
            NdsRomError: Se a ROM não estiver configurada ou não puder ser interpretada.
        """
        return self._rom_instance()

    def close(self) -> None:
        """Fecha os backends abertos."""
        if self._control is not None:
            self._control.close()
            self._control = None
        if self._debugger is not None:
            self._debugger.close()
            self._debugger = None
        if self._rom is not None:
            self._rom.close()
            self._rom = None
