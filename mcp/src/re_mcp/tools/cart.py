"""Tools MCP do cartucho: filesystem (NitroFS) e overlays."""
import os

from ..domain.emulation import CartTrace, TraceError
from ..domain.overlays import Overlay
from ..infra.control import ControlError
from ..infra.ndsrom import NdsRomError
from .app import bridge, error, mcp


@mcp.tool()
def cart_file(offset: int) -> dict:
    """Traduz um offset da ROM no arquivo NitroFS correspondente.

    Parameters:
        offset (int): Offset na ROM (ex.: um endereço lido no trace de cartucho).

    Returns:
        dict: ``{"file": ...}`` ou ``{"error": ...}``.
    """
    try:
        path = bridge.cartfs().file_for_offset(offset)
    except NdsRomError as exc:
        return error(exc)
    if path is None:
        return {"file": None, "error": "offset não pertence a nenhum arquivo NitroFS"}
    return {"file": path}


@mcp.tool()
def cart_list() -> dict:
    """Lista os arquivos do filesystem da ROM (NitroFS).

    Returns:
        dict: ``{"total": N, "files": [{"id", "path"}]}`` ou ``{"error": ...}``.
    """
    try:
        entries = bridge.cartfs().files()
    except NdsRomError as exc:
        return error(exc)
    return {
        "total": len(entries),
        "files": [{"id": entry.file_id, "path": entry.path} for entry in entries],
    }


@mcp.tool()
def cart_read(path: str) -> dict:
    """Lê um arquivo do filesystem da ROM e grava em `/out`.

    Parameters:
        path (str): Caminho do arquivo dentro da ROM (ex.: ``/data/x.sdat``).

    Returns:
        dict: ``{"path", "size"}`` ou ``{"error": ...}``.
    """
    try:
        data = bridge.cartfs().read_file(path)
    except NdsRomError as exc:
        return error(exc)
    out_path = bridge.files().write_bytes(os.path.basename(path) or "cart_file.bin", data)
    return {"path": out_path, "size": len(data)}


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
        channel = bridge.control()
        fs = bridge.cartfs()
    except (ControlError, NdsRomError) as exc:
        return {"error": str(exc)}
    try:
        files = CartTrace(channel).by_file(seconds, fs, batch, timeout_ms)
    except TraceError as exc:
        return {"error": str(exc)}
    return {"total": sum(files.values()), "files": files}


def _overlay_dict(overlay: Overlay) -> dict:
    """Serializa um overlay para o retorno das tools."""
    return {
        "core": overlay.core,
        "index": overlay.index,
        "ram_address": overlay.ram_address,
        "ram_size": overlay.ram_size,
        "bss_size": overlay.bss_size,
        "file_id": overlay.file_id,
    }


@mcp.tool()
def overlay_list(core: str | None = None) -> dict:
    """Lista os overlays da ROM (ARM9 e/ou ARM7).

    Parameters:
        core (str | None): ``arm9``, ``arm7`` ou None para ambos.

    Returns:
        dict: ``{"arm9": [...], "arm7": [...]}`` (ou só o core pedido) ou ``{"error": ...}``.
    """
    try:
        overlays = bridge.overlays()
        cores = [core] if core else ["arm9", "arm7"]
        return {name: [_overlay_dict(o) for o in overlays.overlay_list(name)] for name in cores}
    except NdsRomError as exc:
        return error(exc)


@mcp.tool()
def overlay_for_address(addr: int, core: str = "arm9") -> dict:
    """Resolve um endereço de RAM para o overlay que o contém.

    Parameters:
        addr (int): Endereço de RAM.
        core (str): ``arm9`` ou ``arm7``.

    Returns:
        dict: ``{"overlay": {...}, "offset"}`` ou ``{"overlay": None}``.
    """
    try:
        hit = bridge.overlays().overlay_for_address(addr, core)
    except NdsRomError as exc:
        return error(exc)
    if hit is None:
        return {"overlay": None}
    return {"overlay": _overlay_dict(hit.overlay), "offset": hit.offset}
