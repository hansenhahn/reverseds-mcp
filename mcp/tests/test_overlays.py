"""Overlay table (y9/y7) tests — without the real ROM."""
import struct

from re_mcp.domain.overlays import Overlay, OverlayTable


def _table() -> bytes:
    """A table with two overlays: 0 at 0x02000000 and 1 at 0x02100000."""
    return struct.pack("<8I", 0, 0x02000000, 0x1000, 0x10, 0, 0, 5, 0) + struct.pack(
        "<8I", 1, 0x02100000, 0x2000, 0x20, 0, 0, 6, 0
    )


def test_parse_overlays() -> None:
    """The table becomes the overlay entries."""
    overlays = OverlayTable.from_bytes(_table(), "arm9").entries()
    assert len(overlays) == 2
    assert overlays[0] == Overlay("arm9", 0, 0x02000000, 0x1000, 0x10, 5)
    assert overlays[1].file_id == 6


def test_overlay_covers() -> None:
    """`covers` respects the `[ram_address, +ram_size)` range."""
    overlay = Overlay("arm9", 0, 0x100, 0x10, 0, 0)
    assert overlay.covers(0x108)
    assert not overlay.covers(0x110)


def test_for_address_inside() -> None:
    """An address inside the overlay returns the overlay and the offset."""
    hit = OverlayTable.from_bytes(_table(), "arm9").for_address(0x02000010)
    assert hit is not None
    assert hit.overlay.index == 0
    assert hit.offset == 0x10


def test_for_address_outside() -> None:
    """An address outside the overlays returns None."""
    assert OverlayTable.from_bytes(_table(), "arm9").for_address(0x03000000) is None


def test_parse_sinit_flags_and_compressed_size() -> None:
    """The y9 sinit/flags words are exposed and compression size is masked."""
    data = struct.pack(
        "<8I", 7, 0x02000000, 0x1000, 0, 0x02000010, 0x02000020, 9, 0x03000800
    )
    overlay = OverlayTable.from_bytes(data, "arm9").entries()[0]
    assert overlay.sinit_start == 0x02000010
    assert overlay.sinit_end == 0x02000020
    assert overlay.flags == 0x03000800
    assert overlay.compressed_size == 0x800


def test_candidates_with_shared_base() -> None:
    """All overlays covering an address are returned; `for_address` keeps the first."""
    data = struct.pack(
        "<8I", 0, 0x02000000, 0x1000, 0, 0, 0, 5, 0
    ) + struct.pack("<8I", 1, 0x02000000, 0x2000, 0, 0, 0, 6, 0)
    table = OverlayTable.from_bytes(data, "arm9")
    hits = table.candidates(0x02000010)
    assert [hit.overlay.index for hit in hits] == [0, 1]
    assert [hit.offset_file for hit in hits] == [0x10, 0x10]
    first = table.for_address(0x02000010)
    assert first is not None and first.overlay.index == 0
    by_one = table.by_index(1)
    assert by_one is not None and by_one.file_id == 6
    assert table.by_index(99) is None
