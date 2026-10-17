"""Tools MCP de depuração (gdb): memória, registradores, breakpoints e execução."""
import json

from ..domain.disasm import Disassembler
from ..infra.gdb import DebugError
from .app import bridge, debug_error, error, mcp


@mcp.tool()
def debug_connect(core: str = "arm9") -> dict:
    """Conecta o backend de debug (gdb) ao core escolhido.

    Faz uma leitura de teste do PC após conectar; se o stub não responder,
    desconecta e reporta erro com dica.

    Parameters:
        core (str): ``arm9`` ou ``arm7``.

    Returns:
        dict: ``{"ok": true, "core": ..., "pc": ...}`` ou ``{"error", "hint"?}``.
    """
    try:
        backend = bridge.debugger()
        backend.connect(core)
    except DebugError as exc:
        return debug_error(exc)
    try:
        pc = backend.read_register("pc")
    except DebugError as exc:
        try:
            backend.disconnect()
        except DebugError:
            pass
        return error(
            exc,
            "O stub GDB pode estar travado; reinicie o melonDS (nds-control.sh / nds-debug.sh).",
        )
    return {"ok": True, "core": core, "pc": f"0x{pc:08x}"}


@mcp.tool()
def debug_read_register(name: str = "pc") -> dict:
    """Lê um registrador do core conectado (ex.: ``pc``).

    Parameters:
        name (str): Nome do registrador.

    Returns:
        dict: ``{"name": ..., "value": ...}`` ou ``{"error": ...}``.
    """
    try:
        value = bridge.debugger().read_register(name)
        return {"name": name, "value": value, "value_hex": f"0x{value:08x}"}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_write_register(name: str, value: int) -> dict:
    """Escreve um valor num registrador.

    Parameters:
        name (str): Nome do registrador (ex.: ``pc``).
        value (int): Valor a escrever.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        bridge.debugger().write_register(name, value)
        return {"ok": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def mem_read(addr: int, size: int) -> dict:
    """Lê memória emulada e devolve os bytes em hexadecimal.

    Parameters:
        addr (int): Endereço inicial.
        size (int): Quantidade de bytes.

    Returns:
        dict: ``{"addr": ..., "size": ..., "hex": ...}`` ou ``{"error": ...}``.
    """
    try:
        data = bridge.debugger().read_memory(addr, size)
        return {"addr": addr, "size": len(data), "hex": data.hex()}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def mem_write(addr: int, hex_data: str) -> dict:
    """Escreve bytes (hex) na memória emulada a partir de um endereço.

    Parameters:
        addr (int): Endereço inicial.
        hex_data (str): Bytes em hexadecimal (ex.: ``deadbeef``).

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        bridge.debugger().write_memory(addr, bytes.fromhex(hex_data))
        return {"ok": True}
    except (DebugError, ValueError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def mem_dump_file(addr: int, size: int, name: str | None = None) -> dict:
    """Lê memória e grava um ``.bin`` (e um ``.json``) no diretório de saída.

    Evita trafegar hex gigante pelo MCP: o arquivo vai para ``RE_MCP_OUT_DIR``
    (montado no host, ex.: ``/out``).

    Parameters:
        addr (int): Endereço inicial.
        size (int): Quantidade de bytes.
        name (str | None): Nome do arquivo (default ``dump_<addr>_<size>.bin``).

    Returns:
        dict: ``{"path": ..., "addr": ..., "size": ...}`` ou ``{"error": ...}``.
    """
    try:
        data = bridge.debugger().read_memory(addr, size)
    except DebugError as exc:
        return debug_error(exc)
    filename = (name if name else f"dump_{addr:08x}_{size:x}.bin")
    if not filename.endswith(".bin"):
        filename += ".bin"
    path = bridge.files().write_bytes(filename, data)
    meta = {"path": path, "addr": addr, "size": len(data)}
    bridge.files().write_text(filename + ".json", json.dumps(meta))
    return meta


@mcp.tool()
def disassemble(addr: int, count: int = 16, mode: str = "arm") -> dict:
    """Desmonta ``count`` instruções a partir de ``addr`` (ARM ou Thumb).

    Lê a memória pelo backend de debug — o alvo precisa estar **parado**.

    Parameters:
        addr (int): Endereço inicial.
        count (int): Quantidade de instruções (1..256).
        mode (str): ``arm`` ou ``thumb``.

    Returns:
        dict: ``{"addr", "mode", "instructions": [...]}`` ou ``{"error": ...}``.
    """
    count = max(1, min(count, 256))
    try:
        data = bridge.debugger().read_memory(addr, count * 4)
    except DebugError as exc:
        return debug_error(exc)
    try:
        instructions = Disassembler().disassemble(data, addr, mode, count)
    except ValueError as exc:
        return {"error": str(exc)}
    return {
        "addr": addr,
        "mode": mode,
        "instructions": [
            {
                "address": f"0x{item.address:08x}",
                "size": item.size,
                "bytes": item.bytes_hex,
                "mnemonic": item.mnemonic,
                "op_str": item.op_str,
            }
            for item in instructions
        ],
    }


@mcp.tool()
def set_breakpoint(addr: int) -> dict:
    """Cria um breakpoint de código num endereço.

    Parameters:
        addr (int): Endereço.

    Returns:
        dict: ``{"number": N}`` ou ``{"error": ...}``.
    """
    try:
        return {"number": bridge.debugger().set_breakpoint(addr)}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def set_watchpoint(addr: int, kind: str = "write", condition: str | None = None) -> dict:
    """Cria um watchpoint de hardware (``write``/``read``/``access``).

    Parameters:
        addr (int): Endereço vigiado.
        kind (str): Tipo de acesso.
        condition (str | None): Expressão gdb opcional; o gdb só para quando ela
            for verdadeira (filtra por valor). Ex.:
            ``*(unsigned short*)0x0600F448 != 0``.

    Returns:
        dict: ``{"number": N}`` ou ``{"error": ...}``.
    """
    try:
        return {"number": bridge.debugger().set_watchpoint(addr, kind, condition)}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def remove_breakpoint(number: int) -> dict:
    """Remove um breakpoint/watchpoint pelo número.

    Parameters:
        number (int): Número.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        bridge.debugger().remove(number)
        return {"ok": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_continue(timeout: float = 30.0) -> dict:
    """Retoma a execução e espera a parada (breakpoint/watchpoint).

    Parameters:
        timeout (float): Tempo máximo de espera em segundos.

    Returns:
        dict: ``{"stopped": bool}`` ou ``{"error": ...}``.
    """
    try:
        stopped = bridge.debugger().continue_(timeout)
        return {"stopped": stopped}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_resume() -> dict:
    """Retoma a execução em segundo plano (NÃO bloqueia).

    Diferente de ``debug_continue`` (roda até parar), isto deixa o alvo rodando
    com o gdb ainda conectado, para o agente poder injetar input (canal de
    controle) e depois usar ``debug_wait`` para pegar a parada.

    Returns:
        dict: ``{"ok": true, "running": true}`` ou ``{"error": ...}``.
    """
    try:
        bridge.debugger().resume()
        return {"ok": True, "running": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_wait(timeout: float = 30.0) -> dict:
    """Espera a parada do ``continue`` de fundo (breakpoint/watchpoint).

    Parameters:
        timeout (float): Tempo máximo de espera em segundos.

    Returns:
        dict: ``{"stopped": bool, "running": bool}`` ou ``{"error": ...}``.
    """
    try:
        stopped = bridge.debugger().wait_stop(timeout)
        return {"stopped": stopped, "running": not stopped}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_step() -> dict:
    """Executa uma instrução.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        bridge.debugger().step()
        return {"ok": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_interrupt() -> dict:
    """Interrompe a execução.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        bridge.debugger().interrupt()
        return {"ok": True}
    except DebugError as exc:
        return debug_error(exc)


@mcp.tool()
def debug_disconnect() -> dict:
    """Desconecta o backend de debug — o emulador volta a rodar.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        bridge.debugger().disconnect()
        return {"ok": True}
    except DebugError as exc:
        return debug_error(exc)
