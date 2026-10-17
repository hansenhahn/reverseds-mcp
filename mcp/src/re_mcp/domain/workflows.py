"""Workflows de engenharia reversa assistida (domínio, sem I/O).

Combinam as portas (`Debugger`) e funções puras (diff, símbolos).
"""
from .ports import Debugger
from .types import Symbol, WatchpointHit

_CONTEXT_REGS = ("r0", "r1", "r2", "r3", "sp", "lr")


def find_writer(
    debugger: Debugger, addr: int, timeout: float = 30.0, condition: str | None = None
) -> WatchpointHit | None:
    """Encontra o código que escreve num endereço (watchpoint de escrita).

    Parameters:
        debugger (Debugger): Backend de debug conectado.
        addr (int): Endereço vigiado.
        timeout (float): Tempo máximo de espera em segundos.
        condition (str | None): Expressão gdb opcional (ex.:
            ``*(unsigned short*)0x0600F448 != 0``); só para quando verdadeira.

    Returns:
        WatchpointHit | None: PC e contexto quando parou, ou None se não houve
        escrita no prazo.
    """
    return _find(debugger, addr, "write", timeout, condition)


def find_reader(
    debugger: Debugger, addr: int, timeout: float = 30.0, condition: str | None = None
) -> WatchpointHit | None:
    """Encontra o código que lê um endereço (watchpoint de leitura).

    Parameters:
        debugger (Debugger): Backend de debug conectado.
        addr (int): Endereço vigiado.
        timeout (float): Tempo máximo de espera em segundos.
        condition (str | None): Expressão gdb opcional; só para quando verdadeira.

    Returns:
        WatchpointHit | None: PC e contexto quando parou, ou None se não houve
        leitura no prazo.
    """
    return _find(debugger, addr, "read", timeout, condition)


def _find(
    debugger: Debugger, addr: int, kind: str, timeout: float,
    condition: str | None = None,
) -> WatchpointHit | None:
    number = debugger.set_watchpoint(addr, kind, condition)
    try:
        if not debugger.continue_(timeout):
            return None
        pc = debugger.read_register("pc")
        registers = {name: debugger.read_register(name) for name in _CONTEXT_REGS}
        return WatchpointHit(pc=pc, registers=registers)
    finally:
        debugger.remove(number)


def diff_regions(before: bytes, after: bytes, base: int) -> list[dict]:
    """Compara dois blocos de memória e lista os bytes que mudaram.

    Parameters:
        before (bytes): Bloco anterior.
        after (bytes): Bloco atual.
        base (int): Endereço base do bloco.

    Returns:
        list[dict]: Itens ``{"addr", "old", "new"}`` para cada byte diferente.
    """
    changes = []
    for offset, (old, new) in enumerate(zip(before, after)):
        if old != new:
            changes.append({"addr": base + offset, "old": old, "new": new})
    return changes


def parse_symbols(text: str) -> list[Symbol]:
    """Interpreta um mapa de símbolos (``endereço nome`` por linha).

    Parameters:
        text (str): Conteúdo do `.map` (linhas ``0xADDR nome`` ou ``ADDR nome``).

    Returns:
        list[Symbol]: Os símbolos, ordenados por endereço.
    """
    symbols: list[Symbol] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        try:
            addr = int(parts[0], 16)
        except ValueError:
            continue
        symbols.append(Symbol(addr=addr, name=parts[1].strip()))
    symbols.sort(key=lambda symbol: symbol.addr)
    return symbols


def resolve_symbol(symbols: list[Symbol], addr: int) -> Symbol | None:
    """Devolve o símbolo que contém ``addr`` (maior endereço ≤ ``addr``).

    Parameters:
        symbols (list[Symbol]): Símbolos ordenados por endereço.
        addr (int): Endereço consultado.

    Returns:
        Symbol | None: O símbolo correspondente, ou None.
    """
    found = None
    for symbol in symbols:
        if symbol.addr <= addr:
            found = symbol
        else:
            break
    return found
