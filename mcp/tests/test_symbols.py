"""Symbol table tests (domain)."""
from re_mcp.domain.symbols import Symbol, SymbolTable


def test_resolve_by_nearest() -> None:
    """`resolve` returns the symbol with the largest address ≤ the query."""
    table = SymbolTable.from_map("0x100 foo\n0x200 bar\n; comentário\n")
    assert len(table) == 2
    assert table.resolve(0x180) == Symbol(0x100, "foo")
    assert table.resolve(0x200) == Symbol(0x200, "bar")


def test_resolve_before_first() -> None:
    """An address before the first symbol returns None."""
    table = SymbolTable.from_map("0x100 foo\n")
    assert table.resolve(0x50) is None


def test_ignores_malformed_lines() -> None:
    """Lines without the `address name` pair are ignored."""
    table = SymbolTable.from_map("lixo\n0x10 ok\n")
    assert len(table) == 1


def test_add_replaces_same_address_or_name() -> None:
    """Adding a symbol replaces the same address and removes the same name."""
    table = SymbolTable([])
    table.add(Symbol(0x100, "foo"))
    table.add(Symbol(0x100, "bar"))
    assert len(table) == 1
    assert table.resolve(0x100) == Symbol(0x100, "bar")
    table.add(Symbol(0x200, "bar"))
    assert len(table) == 1
    assert table.resolve(0x200) == Symbol(0x200, "bar")


def test_merge_and_json_roundtrip() -> None:
    """Metadata survives merge and JSON serialization."""
    table = SymbolTable([Symbol(0x100, "foo", "function", "note", 22)])
    table.merge(SymbolTable([Symbol(0x200, "bar", "data")]))
    restored = SymbolTable.from_json(table.to_json())
    assert len(restored) == 2
    assert restored.resolve(0x100) == Symbol(0x100, "foo", "function", "note", 22)
    bar = restored.resolve(0x200)
    assert bar is not None and bar.kind == "data"


def test_invalid_json_raises() -> None:
    """Malformed persisted data is rejected."""
    import pytest
    with pytest.raises(ValueError):
        SymbolTable.from_json("{not json")


def test_by_name() -> None:
    """`by_name` finds an exact symbol name."""
    table = SymbolTable([Symbol(0x100, "foo"), Symbol(0x200, "bar")])
    assert table.by_name("bar") == Symbol(0x200, "bar")
    assert table.by_name("nope") is None


def test_same_address_different_overlays_coexist() -> None:
    """Adding the same address in another overlay does not replace the first."""
    table = SymbolTable([])
    table.add(Symbol(0x020A11C4, "fn_22", overlay=22))
    table.add(Symbol(0x020A11C4, "fn_25", overlay=25))
    assert len(table) == 2
    assert table.resolve(0x020A11C4, 22) == Symbol(0x020A11C4, "fn_22", overlay=22)
    assert table.resolve(0x020A11C4, 25) == Symbol(0x020A11C4, "fn_25", overlay=25)


def test_ambiguous_without_overlay() -> None:
    """Without an overlay filter, two symbols at the address are ambiguous."""
    table = SymbolTable(
        [
            Symbol(0x020A11C4, "fn_22", overlay=22),
            Symbol(0x020A11C4, "fn_25", overlay=25),
        ]
    )
    assert table.resolve(0x020A11C4) is None
    assert [s.name for s in table.candidates(0x020A11C4)] == ["fn_22", "fn_25"]


def test_global_symbol_is_fallback() -> None:
    """A global symbol resolves when there is no specific one for the overlay."""
    table = SymbolTable([Symbol(0x02000000, "global")])
    assert table.resolve(0x02000000, 25) == Symbol(0x02000000, "global")
    table.add(Symbol(0x02000000, "fn_25", overlay=25))
    assert table.resolve(0x02000000, 25) == Symbol(0x02000000, "fn_25", overlay=25)
    assert table.resolve(0x02000000, 22) == Symbol(0x02000000, "global")


def test_replace_overlay_keeps_other_overlays() -> None:
    """Replacing one overlay preserves globals and other overlays."""
    table = SymbolTable(
        [
            Symbol(0x100, "global"),
            Symbol(0x100, "fn_22", overlay=22),
            Symbol(0x100, "fn_25_old", overlay=25),
        ]
    )
    table.replace_overlay(
        25, SymbolTable([Symbol(0x100, "fn_25_new", overlay=25)])
    )
    assert table.resolve(0x100, 25) == Symbol(0x100, "fn_25_new", overlay=25)
    assert table.resolve(0x100, 22) == Symbol(0x100, "fn_22", overlay=22)
    assert table.resolve(0x100, 99) == Symbol(0x100, "global")


def test_json_roundtrip_with_same_address_overlays() -> None:
    """The persisted table keeps both overlay-scoped symbols."""
    table = SymbolTable(
        [
            Symbol(0x020A11C4, "fn_22", overlay=22),
            Symbol(0x020A11C4, "fn_25", overlay=25),
        ]
    )
    restored = SymbolTable.from_json(table.to_json())
    assert len(restored) == 2
    assert restored.resolve(0x020A11C4, 22) == Symbol(0x020A11C4, "fn_22", overlay=22)
    assert restored.resolve(0x020A11C4, 25) == Symbol(0x020A11C4, "fn_25", overlay=25)
