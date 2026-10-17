"""Tools MCP do canal de controle: ping, input, tela, savestate, execução e trace."""
import io

from PIL import Image

from ..application.cart_trace import CartTrace
from ..application.input import InputMacros
from ..domain.input import InputStep
from ..infra.control import ControlError
from ..infra.gdb import DebugError
from .app import bridge, control_call, error, mcp

_CONTROL_HINT = "Verifique se o melonDS está rodando com o canal de controle habilitado."


@mcp.tool()
def ping() -> dict:
    """Verifica a conexão com o canal de controle do melonDS.

    Returns:
        dict: ``{"pong": true}`` quando o emulador responde, ou ``{"error": ...}``.
    """
    return control_call("ping")


@mcp.tool()
def health_check() -> dict:
    """Checa o canal de controle e o debugger, com dicas de diagnóstico.

    Não cria nem derruba conexões: usa o canal atual e, se o debugger estiver
    conectado, faz uma leitura de teste do PC.

    Returns:
        dict: ``{"control": ..., "debug": ...}`` com ``error``/``hint`` por backend.
    """
    out: dict = {}
    try:
        out["control"] = bridge.control().call("ping")
    except ControlError as exc:
        out["control"] = error(exc, "O melonDS está rodando com o canal de controle?")
    debugger = bridge.debugger()
    if debugger.is_running():
        out["debug"] = {"ok": True, "running": True}
    else:
        try:
            pc = debugger.read_register("pc")
            out["debug"] = {"ok": True, "pc": f"0x{pc:08x}"}
        except DebugError as exc:
            out["debug"] = error(
                exc, "Chame debug_connect() (ou reinicie o melonDS se o stub caiu)."
            )
    return out


@mcp.tool()
def input_key(mask: int) -> dict:
    """Define as teclas pressionadas (máscara active-low: 1=solto, 0=pressionado).

    Parameters:
        mask (int): Máscara (0xFFF = nada; ex.: 0xFF7 = Start).

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return control_call("input.key", {"mask": mask})


@mcp.tool()
def input_touch(x: int, y: int) -> dict:
    """Pressiona a tela de toque em (x, y).

    Parameters:
        x (int): Coordenada x.
        y (int): Coordenada y.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return control_call("input.touch", {"x": x, "y": y})


@mcp.tool()
def input_release() -> dict:
    """Solta todas as teclas e a tela de toque.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return control_call("input.release")


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
        channel = bridge.control()
    except ControlError as exc:
        return error(exc, _CONTROL_HINT)
    try:
        InputMacros(channel).tap(mask, ms)
        return {"ok": True}
    except ControlError as exc:
        return error(exc, _CONTROL_HINT)


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
        channel = bridge.control()
    except ControlError as exc:
        return error(exc, _CONTROL_HINT)
    try:
        parsed = [
            InputStep(
                ms=int(step.get("ms", 100)),
                after_ms=int(step.get("after_ms", 0)),
                mask=(int(step["mask"]) if step.get("mask") is not None else None),
            )
            for step in steps
        ]
        InputMacros(channel).run(parsed)
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
    return control_call("input.merge", {"enabled": enabled})


@mcp.tool()
def screen_capture(screens: str = "both", format: str = "rgba8") -> dict:
    """Captura a(s) tela(s) sob demanda e salva como PNG.

    Parameters:
        screens (str): ``top``, ``bottom`` ou ``both``.
        format (str): ``rgba8`` ou ``bgra8``.

    Returns:
        dict: ``{"paths": [...]}`` com os PNGs salvos, ou ``{"error": ...}``.
    """
    result = control_call("screen.capture", {"screens": screens, "format": format})
    if "error" in result:
        if "timed out" in str(result["error"]).lower():
            result["hint"] = (
                "A captura expirou: a CPU pode estar parada (use debug_resume() ou "
                "debug_disconnect()) ou o renderer não é software."
            )
        return result

    binary = result.get("binary", {})
    data = binary.get("data", b"")
    width = binary.get("width", 256)
    height = binary.get("height", 192)
    raw_mode = "RGBA" if format == "rgba8" else "BGRA"
    frame = width * height * 4
    paths: list[str] = []
    for index in range(len(data) // frame):
        image = Image.frombuffer(
            "RGBA", (width, height),
            data[index * frame:(index + 1) * frame],
            "raw", raw_mode, 0, 1,
        )
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        paths.append(bridge.files().write_bytes(f"capture_{index}.png", buffer.getvalue()))
    return {"paths": paths}


@mcp.tool()
def savestate_save(slot: int = 0) -> dict:
    """Salva o estado da emulação num slot.

    Parameters:
        slot (int): Identificador do slot.

    Returns:
        dict: ``{"ok": true, "path": ...}`` ou ``{"error": ...}``.
    """
    return control_call("savestate.save", {"slot": slot})


@mcp.tool()
def savestate_load(slot: int = 0) -> dict:
    """Carrega o estado da emulação de um slot.

    Parameters:
        slot (int): Identificador do slot.

    Returns:
        dict: ``{"ok": true, "path": ...}`` ou ``{"error": ...}``.
    """
    return control_call("savestate.load", {"slot": slot})


@mcp.tool()
def emu_pause() -> dict:
    """Pausa a execução.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return control_call("emu.pause")


@mcp.tool()
def emu_resume() -> dict:
    """Retoma a execução.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return control_call("emu.resume")


@mcp.tool()
def cart_trace_start(batch: int = 256, timeout_ms: int = 100) -> dict:
    """Inicia o trace de leitura do cartucho (subscreve).

    Parameters:
        batch (int): Itens por lote.
        timeout_ms (int): Timeout do lote em milissegundos.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return control_call("cart.trace.start", {"batch": batch, "timeout_ms": timeout_ms})


@mcp.tool()
def cart_trace_read(seconds: float = 2.0) -> dict:
    """Coleta as leituras do cartucho por um período (lotes ``event.cart``).

    Parameters:
        seconds (float): Duração da coleta em segundos.

    Returns:
        dict: ``{"count": N, "reads": [...]}`` ou ``{"error": ...}``.
    """
    try:
        channel = bridge.control()
    except ControlError as exc:
        return error(exc, _CONTROL_HINT)
    reads = CartTrace(channel).collect(seconds)
    return {"count": len(reads), "reads": reads}


@mcp.tool()
def cart_trace_stop() -> dict:
    """Para o trace de leitura do cartucho.

    Returns:
        dict: ``{"ok": true}`` ou ``{"error": ...}``.
    """
    return control_call("cart.trace.stop")
