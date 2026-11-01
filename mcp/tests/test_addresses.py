"""Pure address parsing/region tests — no emulator."""
import pytest

from re_mcp.domain.addresses import NDS9_REGIONS, AddressSpace


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0x020A2D90, 0x020A2D90),
        ("0x020A2D90", 0x020A2D90),
        ("020A2D90", 0x020A2D90),
        ("34253200", 34253200),
        ("0x1_000", 0x1000),
        ("  0x20  ", 0x20),
    ],
)
def test_parse_address_accepts_hex_and_decimal(value: object, expected: int) -> None:
    """Hex (prefixed or bare) and decimal text are accepted."""
    assert AddressSpace.parse(value) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    ["", "   ", "zzz", "-1", "0x100000000", "0x", True, 0x1_0000_0000, 1.5],
)
def test_parse_address_rejects_invalid_values(value: object) -> None:
    """Invalid, negative, out-of-range or non-string/int values are rejected."""
    with pytest.raises(ValueError):
        AddressSpace.parse(value)  # type: ignore[arg-type]


def test_describe_main_ram_is_aligned_and_mapped() -> None:
    """Main RAM resolves to its region and 4-byte alignment."""
    info = AddressSpace.describe(0x020A2D90)
    assert info.value_hex == "0x020a2d90"
    assert info.aligned4 is True
    assert info.mapped is True
    assert info.region is not None and info.region.name == "main-ram"


def test_describe_unaligned_address() -> None:
    """A non-multiple-of-4 address is reported as unaligned."""
    assert AddressSpace.describe(0x02000001).aligned4 is False


def test_describe_unmapped_address_is_not_an_error() -> None:
    """An address outside the known regions is a valid result with mapped=False."""
    info = AddressSpace.describe(0x01000000)
    assert info.mapped is False
    assert info.region is None


@pytest.mark.parametrize(
    ("addr", "region"),
    [
        (0x07000210, "oam"),
        (0x06000300, "vram-a-bg"),
        (0x06400300, "vram-a-obj"),
        (0x05000200, "palettes"),
        (0x04000000, "io"),
        (0xFFFF0000, "arm9-bios"),
    ],
)
def test_region_for_known_ranges(addr: int, region: str) -> None:
    """Known ARM9 windows resolve to their region name."""
    found = AddressSpace.region_for(addr)
    assert found is not None and found.name == region


def test_regions_do_not_overlap_and_are_sorted() -> None:
    """The static map is ordered and non-overlapping (catches table mistakes)."""
    ordered = sorted(NDS9_REGIONS, key=lambda item: item.start)
    assert ordered == list(NDS9_REGIONS)
    for previous, current in zip(ordered, ordered[1:]):
        assert previous.end < current.start
