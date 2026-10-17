"""Testes das tabelas de overlay (`y9`/`y7`) — sem a ROM real."""
import struct

from re_mcp.domain.overlays import Overlay, parse_overlays, resolve_address


def _table() -> bytes:
    """Tabela com dois overlays: 0 em 0x02000000 e 1 em 0x02100000."""
    return struct.pack("<8I", 0, 0x02000000, 0x1000, 0x10, 0, 0, 5, 0) + struct.pack(
        "<8I", 1, 0x02100000, 0x2000, 0x20, 0, 0, 6, 0
    )


def test_parse_overlays() -> None:
    """A tabela vira as entradas de overlay."""
    overlays = parse_overlays(_table(), "arm9")
    assert len(overlays) == 2
    assert overlays[0] == Overlay("arm9", 0, 0x02000000, 0x1000, 0x10, 5)
    assert overlays[1].file_id == 6


def test_resolve_address_inside() -> None:
    """Um endereço dentro do overlay devolve o overlay e o deslocamento."""
    overlays = parse_overlays(_table(), "arm9")
    hit = resolve_address(overlays, 0x02000010)
    assert hit is not None
    assert hit.overlay.index == 0
    assert hit.offset == 0x10


def test_resolve_address_outside() -> None:
    """Um endereço fora dos overlays devolve None."""
    overlays = parse_overlays(_table(), "arm9")
    assert resolve_address(overlays, 0x03000000) is None
