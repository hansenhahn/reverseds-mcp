"""Ponte: mantém os backends (canal de controle e gdb) e o ciclo de vida.

Acesso preguiçoso (lazy): a conexão só é aberta na primeira chamada, para o MCP
subir mesmo sem emulador rodando.
"""
from .config import Config
from .domain.ports import CartFs, ControlChannel, Debugger, Overlays
from .domain.types import Symbol
from .infra.control import UnixControlChannel
from .infra.gdb import GdbBackend
from .infra.ndsrom import NdsRom, NdsRomError


class Bridge:
    """Acesso lazy aos backends do emulador."""

    def __init__(self, config: Config) -> None:
        """Guarda a configuração.

        Parameters:
            config (Config): Configuração dos backends.
        """
        self._config = config
        self._control: ControlChannel | None = None
        self._debugger: Debugger | None = None
        self._symbols: list[Symbol] = []
        self._snapshots: dict[str, tuple[int, bytes]] = {}
        self._rom: NdsRom | None = None

    @property
    def config(self) -> Config:
        """A configuração em uso."""
        return self._config

    def symbols(self) -> list[Symbol]:
        """Os símbolos carregados (via `symbol_load`)."""
        return self._symbols

    def set_symbols(self, symbols: list[Symbol]) -> None:
        """Substitui o conjunto de símbolos.

        Parameters:
            symbols (list[Symbol]): Símbolos ordenados por endereço.
        """
        self._symbols = symbols

    def snapshots(self) -> dict[str, tuple[int, bytes]]:
        """As capturas de memória guardadas (nome -> (base, bytes))."""
        return self._snapshots

    def _rom_instance(self) -> NdsRom:
        if self._rom is None:
            if not self._config.rom_path:
                raise NdsRomError("ROM não configurada (defina RE_MCP_ROM)")
            self._rom = NdsRom(self._config.rom_path)
        return self._rom

    def nitrofs(self) -> CartFs:
        """Devolve o filesystem da ROM (NitroFS), abrindo-o na primeira chamada.

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
