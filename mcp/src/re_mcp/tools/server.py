"""Servidor MCP: expõe as tools de engenharia reversa assistida.

As tools são finas: delegam para a ponte (`Bridge`) e para o domínio.
"""
import json
import os
import time

from mcp.server.mcpserver import MCPServer

from ..bridge import Bridge
from ..config import Config
from ..domain import disasm, workflows
from ..domain import input as input_macros
from ..infra.control import ControlError
from ..infra.gdb import DebugError
from ..infra.nitrofs import NitroFsError

_bridge = Bridge(Config.from_env())

mcp = MCPServer("re-mcp")

_OUT_DIR = os.environ.get("RE_MCP_OUT_DIR", "/tmp/re_mcp")


def _control(method: str, params: dict | None = None) -> dict:
    """Chama o canal de controle, convertendo erro em dicionário.

    Parameters:
        method (str): Método do canal de controle.
        params (dict | None): Parâmetros.

    Returns:
        dict: O resultado, ou ``{"error": ...}``.
    """
    try:
        return _bridge.control().call(method, params)
    except ControlError as exc:
        return {"error": str(exc)}


@mcp.tool()
def ping() -> dict:
    """Verifica a conexão com o canal de controle do melonDS.

    Returns:
        dict: ``{"pong": true}`` quando o emulador responde, ou ``{"error": ...}``.
    """
    try:
        return _bridge.control().call("ping")
    except ControlError as exc:
        return {"error": str(exc)}


@mcp.tool()
def debug_connect(core: str = "arm9") -> dict:
    """Conecta o backend de debug (gdb) ao core escolhido.

    Parameters:
        core (str): ``arm9`` ou ``arm7``.

    Returns:
        dict: ``{"ok": true, "core": ...}`` ou ``{"error": ...}``.
    """
    try:
        _bridge.debugger().connect(core)
        return {"ok": True, "core": core}
    except DebugError as exc:
        return {"error": str(exc)}


@mcp.tool()
def debug_read_register(name: str = "pc") -> dict:
    """Lê um registrador do core conectado (ex.: ``pc``).

    Parameters:
        name (str): Nome do registrador.

    Returns:
        dict: ``{"name": ..., "value": ...}`` ou ``{"error": ...}``.
    """
    try:
        value = _bridge.debugger().read_register(name)
        return {"name": name, "value": value, "value_hex": f"0x{value:08x}"}
    except DebugError as exc:
        return {"error": str(exc)}


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
        _bridge.debugger().write_register(name, value)
        return {"ok": True}
    except DebugError as exc:
        return {"error": str(exc)}


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
        data = _bridge.debugger().read_memory(addr, size)
        return {"addr": addr, "size": len(data), "hex": data.hex()}
    except DebugError as exc:
        return {"error": str(exc)}


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
        _bridge.debugger().write_memory(addr, bytes.fromhex(hex_data))
        return {"ok": True}
    except (DebugError, ValueError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def mem_dump_file(addr: int, size: int, name: str | None = None) -> dict:
    """Lê memória e grava um ``.bin`` (e um ``.json`` de metadados) no diretório de saída.

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
        data = _bridge.debugger().read_memory(addr, size)
    except DebugError as exc:
        return {"error": str(exc)}
    os.makedirs(_OUT_DIR, exist_ok=True)
    filename = os.path.basename(name) if name else f"dump_{addr:08x}_{size:x}.bin"
    if not filename.endswith(".bin"):
        filename += ".bin"
    path = os.path.join(_OUT_DIR, filename)
    with open(path, "wb") as handle:
        handle.write(data)
    meta = {"path": path, "addr": addr, "size": len(data)}
    with open(path + ".json", "w", encoding="utf-8") as handle:
        json.dump(meta, handle)
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
    size = count * 4
    try:
        data = _bridge.debugger().read_memory(addr, size)
    except DebugError as exc:
        return {"error": str(exc)}
    try:
        instructions = disasm.disassemble(data, addr, mode, count)
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
        return {"number": _bridge.debugger().set_breakpoint(addr)}
    except DebugError as exc:
        return {"error": str(exc)}


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
        return {"number": _bridge.debugger().set_watchpoint(addr, kind, condition)}
    except DebugError as exc:
        return {"error": str(exc)}


@mcp.tool()
def remove_breakpoint(number: int) -> dict:
    """Remove um breakpoint/watchpoint pelo número.

    Parameters:
        number (int): Número.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        _bridge.debugger().remove(number)
        return {"ok": True}
    except DebugError as exc:
        return {"error": str(exc)}


@mcp.tool()
def debug_continue(timeout: float = 30.0) -> dict:
    """Retoma a execução e espera a parada (breakpoint/watchpoint).

    Parameters:
        timeout (float): Tempo máximo de espera em segundos.

    Returns:
        dict: ``{"stopped": bool}`` ou ``{"error": ...}``.
    """
    try:
        stopped = _bridge.debugger().continue_(timeout)
        return {"stopped": stopped}
    except DebugError as exc:
        return {"error": str(exc)}


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
        _bridge.debugger().resume()
        return {"ok": True, "running": True}
    except DebugError as exc:
        return {"error": str(exc)}


@mcp.tool()
def debug_wait(timeout: float = 30.0) -> dict:
    """Espera a parada do ``continue`` de fundo (breakpoint/watchpoint).

    Parameters:
        timeout (float): Tempo máximo de espera em segundos.

    Returns:
        dict: ``{"stopped": bool, "running": bool}`` ou ``{"error": ...}``.
    """
    try:
        stopped = _bridge.debugger().wait_stop(timeout)
        return {"stopped": stopped, "running": not stopped}
    except DebugError as exc:
        return {"error": str(exc)}


@mcp.tool()
def debug_step() -> dict:
    """Executa uma instrução.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        _bridge.debugger().step()
        return {"ok": True}
    except DebugError as exc:
        return {"error": str(exc)}


@mcp.tool()
def debug_interrupt() -> dict:
    """Interrompe a execução.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        _bridge.debugger().interrupt()
        return {"ok": True}
    except DebugError as exc:
        return {"error": str(exc)}


@mcp.tool()
def debug_disconnect() -> dict:
    """Desconecta o backend de debug — o emulador volta a rodar.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        _bridge.debugger().disconnect()
        return {"ok": True}
    except DebugError as exc:
        return {"error": str(exc)}


@mcp.tool()
def input_key(mask: int) -> dict:
    """Define as teclas pressionadas (máscara active-low: 1=solto, 0=pressionado).

    Parameters:
        mask (int): Máscara (0xFFF = nada; ex.: 0xFF7 = Start).

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return _control("input.key", {"mask": mask})


@mcp.tool()
def input_touch(x: int, y: int) -> dict:
    """Pressiona a tela de toque em (x, y).

    Parameters:
        x (int): Coordenada x.
        y (int): Coordenada y.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return _control("input.touch", {"x": x, "y": y})


@mcp.tool()
def input_release() -> dict:
    """Solta todas as teclas e a tela de toque.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return _control("input.release")


@mcp.tool()
def input_tap(mask: int, ms: int = 100) -> dict:
    """Aperta a(s) tecla(s) da máscara por ``ms`` e solta (macro de input).

    Parameters:
        mask (int): Máscara active-low (ex.: ``0xFF7`` = Start).
        ms (int): Duração do toque em milissegundos.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    try:
        channel = _bridge.control()
    except ControlError as exc:
        return {"error": str(exc)}
    try:
        input_macros.tap(channel, mask, ms)
        return {"ok": True}
    except ControlError as exc:
        return {"error": str(exc)}


@mcp.tool()
def input_sequence(steps: list[dict]) -> dict:
    """Executa uma sequência de passos ``{mask, ms, after_ms}`` (macro de input).

    Cada passo aperta ``mask``, espera ``ms``, solta e espera ``after_ms``. Passo
    sem ``mask`` apenas espera. O input é solto ao final (mesmo em erro).

    Parameters:
        steps (list[dict]): Lista ordenada de passos.

    Returns:
        dict: ``{"ok": true, "steps": N}`` ou ``{"error": ...}``.
    """
    try:
        channel = _bridge.control()
    except ControlError as exc:
        return {"error": str(exc)}
    try:
        parsed = [
            input_macros.InputStep(
                ms=int(step.get("ms", 100)),
                after_ms=int(step.get("after_ms", 0)),
                mask=(int(step["mask"]) if step.get("mask") is not None else None),
            )
            for step in steps
        ]
        input_macros.sequence(channel, parsed)
        return {"ok": True, "steps": len(parsed)}
    except (ControlError, ValueError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def input_merge(enabled: bool = True) -> dict:
    """Liga/desliga a mesclagem do input do agente com o do host.

    Parameters:
        enabled (bool): True mescla (humano + agente); False deixa o agente sozinho.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return _control("input.merge", {"enabled": enabled})


@mcp.tool()
def screen_capture(screens: str = "both", format: str = "rgba8") -> dict:
    """Captura a(s) tela(s) sob demanda e salva como PNG.

    Parameters:
        screens (str): ``top``, ``bottom`` ou ``both``.
        format (str): ``rgba8`` ou ``bgra8``.

    Returns:
        dict: ``{"paths": [...]}`` com os PNGs salvos, ou ``{"error": ...}``.
    """
    result = _control("screen.capture", {"screens": screens, "format": format})
    if "error" in result:
        return result

    binary = result.get("binary", {})
    data = binary.get("data", b"")
    width = binary.get("width", 256)
    height = binary.get("height", 192)

    from PIL import Image

    raw_mode = "RGBA" if format == "rgba8" else "BGRA"
    frame = width * height * 4
    os.makedirs(_OUT_DIR, exist_ok=True)
    paths: list[str] = []
    for index in range(len(data) // frame):
        image = Image.frombuffer(
            "RGBA", (width, height),
            data[index * frame:(index + 1) * frame],
            "raw", raw_mode, 0, 1,
        )
        path = os.path.join(_OUT_DIR, f"capture_{index}.png")
        image.save(path)
        paths.append(path)
    return {"paths": paths}


@mcp.tool()
def savestate_save(slot: int = 0) -> dict:
    """Salva o estado da emulação num slot.

    Parameters:
        slot (int): Identificador do slot.

    Returns:
        dict: ``{"ok": true, "path": ...}`` ou ``{"error": ...}``.
    """
    return _control("savestate.save", {"slot": slot})


@mcp.tool()
def savestate_load(slot: int = 0) -> dict:
    """Carrega o estado da emulação de um slot.

    Parameters:
        slot (int): Identificador do slot.

    Returns:
        dict: ``{"ok": true, "path": ...}`` ou ``{"error": ...}``.
    """
    return _control("savestate.load", {"slot": slot})


@mcp.tool()
def emu_pause() -> dict:
    """Pausa a execução.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return _control("emu.pause")


@mcp.tool()
def emu_resume() -> dict:
    """Retoma a execução.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return _control("emu.resume")


@mcp.tool()
def cart_trace_start(batch: int = 256, timeout_ms: int = 100) -> dict:
    """Inicia o trace de leitura do cartucho (subscreve).

    Parameters:
        batch (int): Itens por lote.
        timeout_ms (int): Timeout do lote em milissegundos.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return _control("cart.trace.start", {"batch": batch, "timeout_ms": timeout_ms})


@mcp.tool()
def cart_trace_read(seconds: float = 2.0) -> dict:
    """Coleta as leituras do cartucho por um período (lotes ``event.cart``).

    Parameters:
        seconds (float): Duração da coleta em segundos.

    Returns:
        dict: ``{"count": N, "reads": [...]}`` ou ``{"error": ...}``.
    """
    try:
        channel = _bridge.control()
    except ControlError as exc:
        return {"error": str(exc)}

    reads: list[dict] = []
    deadline = time.monotonic() + seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        message = channel.read_message(timeout=min(0.5, remaining))
        if message is not None and message.get("method") == "event.cart":
            reads.extend(message["params"]["reads"])
    return {"count": len(reads), "reads": reads}


@mcp.tool()
def cart_trace_stop() -> dict:
    """Para o trace de leitura do cartucho.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return _control("cart.trace.stop")


@mcp.tool()
def find_writer(addr: int, timeout: float = 30.0, condition: str | None = None) -> dict:
    """Acha o código que ESCREVE num endereço (watchpoint de escrita + run).

    Parameters:
        addr (int): Endereço vigiado.
        timeout (float): Tempo máximo de espera em segundos.
        condition (str | None): Expressão gdb opcional; só para quando verdadeira
            (ex.: ``*(unsigned short*)0x0600F448 != 0`` para pular escritas de 0).

    Returns:
        dict: ``{"hit": {"pc", "registers"}}`` se parou, ``{"hit": null}`` se não houve
        escrita no prazo, ou ``{"error": ...}``.
    """
    try:
        hit = workflows.find_writer(_bridge.debugger(), addr, timeout, condition)
    except DebugError as exc:
        return {"error": str(exc)}
    if hit is None:
        return {"hit": None}
    return {"hit": {"pc": hit.pc, "pc_hex": f"0x{hit.pc:08x}", "registers": hit.registers}}


@mcp.tool()
def find_reader(addr: int, timeout: float = 30.0, condition: str | None = None) -> dict:
    """Acha o código que LÊ um endereço (watchpoint de leitura + run).

    Parameters:
        addr (int): Endereço vigiado.
        timeout (float): Tempo máximo de espera em segundos.
        condition (str | None): Expressão gdb opcional; só para quando verdadeira.

    Returns:
        dict: ``{"hit": {"pc", "registers"}}`` se parou, ``{"hit": null}`` se não houve
        leitura no prazo, ou ``{"error": ...}``.
    """
    try:
        hit = workflows.find_reader(_bridge.debugger(), addr, timeout, condition)
    except DebugError as exc:
        return {"error": str(exc)}
    if hit is None:
        return {"hit": None}
    return {"hit": {"pc": hit.pc, "pc_hex": f"0x{hit.pc:08x}", "registers": hit.registers}}


@mcp.tool()
def mem_snapshot(name: str, addr: int, size: int) -> dict:
    """Guarda um bloco de memória para comparar depois (`state_diff`).

    Parameters:
        name (str): Nome da captura.
        addr (int): Endereço base.
        size (int): Tamanho em bytes.

    Returns:
        dict: ``{"ok": true, "name": ..., "size": ...}`` ou ``{"error": ...}``.
    """
    try:
        data = _bridge.debugger().read_memory(addr, size)
    except DebugError as exc:
        return {"error": str(exc)}
    _bridge.snapshots()[name] = (addr, data)
    return {"ok": True, "name": name, "size": len(data)}


@mcp.tool()
def state_diff(name: str) -> dict:
    """Compara a memória atual com uma captura (`mem_snapshot`) e lista o que mudou.

    Parameters:
        name (str): Nome da captura a comparar.

    Returns:
        dict: ``{"changes": [...], "count": N}`` ou ``{"error": ...}``.
    """
    snapshot = _bridge.snapshots().get(name)
    if snapshot is None:
        return {"error": f"captura '{name}' não existe"}
    base, before = snapshot
    try:
        after = _bridge.debugger().read_memory(base, len(before))
    except DebugError as exc:
        return {"error": str(exc)}
    changes = workflows.diff_regions(before, after, base)
    return {"changes": changes, "count": len(changes)}


@mcp.tool()
def symbol_load(path: str) -> dict:
    """Carrega um mapa de símbolos (`.map`) para resolver endereços.

    Parameters:
        path (str): Caminho do arquivo `.map` (linhas ``endereço nome``).

    Returns:
        dict: ``{"ok": true, "count": N}`` ou ``{"error": ...}``.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            symbols = workflows.parse_symbols(handle.read())
    except OSError as exc:
        return {"error": str(exc)}
    _bridge.set_symbols(symbols)
    return {"ok": True, "count": len(symbols)}


@mcp.tool()
def symbol_lookup(addr: int) -> dict:
    """Resolve um endereço para o símbolo que o contém.

    Parameters:
        addr (int): Endereço consultado.

    Returns:
        dict: ``{"name": ..., "addr": ...}`` ou ``{"error": ...}``.
    """
    symbol = workflows.resolve_symbol(_bridge.symbols(), addr)
    if symbol is None:
        return {"error": "nenhum símbolo contém esse endereço"}
    return {"name": symbol.name, "addr": symbol.addr, "addr_hex": f"0x{symbol.addr:08x}"}


@mcp.tool()
def cart_file(offset: int) -> dict:
    """Traduz um offset da ROM no arquivo NitroFS correspondente.

    Parameters:
        offset (int): Offset na ROM (ex.: um endereço lido no trace de cartucho).

    Returns:
        dict: ``{"file": ...}`` ou ``{"error": ...}``.
    """
    try:
        path = _bridge.nitrofs().file_for_offset(offset)
    except NitroFsError as exc:
        return {"error": str(exc)}
    if path is None:
        return {"file": None, "error": "offset não pertence a nenhum arquivo NitroFS"}
    return {"file": path}


@mcp.tool()
def cart_read_files(seconds: float = 3.0, batch: int = 256, timeout_ms: int = 100) -> dict:
    """Monitora leituras do cartucho por um período e agrega por arquivo NitroFS.

    Inicia o trace, coleta as leituras, para, e agrupa por arquivo.

    Parameters:
        seconds (float): Duração da coleta em segundos.
        batch (int): Itens por lote.
        timeout_ms (int): Timeout do lote em milissegundos.

    Returns:
        dict: ``{"total": N, "files": {arquivo: contagem}}`` ou ``{"error": ...}``.
    """
    try:
        channel = _bridge.control()
        nitrofs = _bridge.nitrofs()
    except (ControlError, NitroFsError) as exc:
        return {"error": str(exc)}

    started = channel.call("cart.trace.start", {"batch": batch, "timeout_ms": timeout_ms})
    if "error" in started:
        return started

    files: dict[str, int] = {}
    total = 0
    deadline = time.monotonic() + seconds
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            message = channel.read_message(timeout=min(0.5, remaining))
            if message is None or message.get("method") != "event.cart":
                continue
            for read in message["params"]["reads"]:
                total += 1
                path = nitrofs.file_for_offset(read["addr"])
                key = path or "<não-arquivo>"
                files[key] = files.get(key, 0) + 1
    finally:
        channel.call("cart.trace.stop")
    return {"total": total, "files": files}
