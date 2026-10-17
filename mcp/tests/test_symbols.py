"""Testes da tabela de símbolos (domínio)."""
from re_mcp.domain.symbols import Symbol, SymbolTable


def test_resolve_by_nearest() -> None:
    """`resolve` devolve o símbolo de maior endereço ≤ consultado."""
    table = SymbolTable.from_map("0x100 foo\n0x200 bar\n; comentário\n")
    assert len(table) == 2
    assert table.resolve(0x180) == Symbol(0x100, "foo")
    assert table.resolve(0x200) == Symbol(0x200, "bar")


def test_resolve_before_first() -> None:
    """Endereço antes do primeiro símbolo devolve None."""
    table = SymbolTable.from_map("0x100 foo\n")
    assert table.resolve(0x50) is None


def test_ignores_malformed_lines() -> None:
    """Linhas sem par `endereço nome` são ignoradas."""
    table = SymbolTable.from_map("lixo\n0x10 ok\n")
    assert len(table) == 1
