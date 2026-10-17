"""Símbolos: um mapa de endereços → nomes (value object, sem I/O)."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Symbol:
    """Símbolo: um nome para um endereço."""

    addr: int
    name: str


class SymbolTable:
    """Tabela de símbolos ordenada por endereço, com resolução por proximidade."""

    def __init__(self, symbols: list[Symbol]) -> None:
        self._symbols = sorted(symbols, key=lambda symbol: symbol.addr)

    @classmethod
    def from_map(cls, text: str) -> "SymbolTable":
        """Interpreta um mapa de símbolos (``endereço nome`` por linha).

        Parameters:
            text (str): Conteúdo do `.map` (linhas ``0xADDR nome`` ou ``ADDR nome``).

        Returns:
            SymbolTable: A tabela de símbolos.
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
        return cls(symbols)

    def resolve(self, addr: int) -> Symbol | None:
        """O símbolo que contém ``addr`` (maior endereço ≤ ``addr``), ou None.

        Parameters:
            addr (int): Endereço consultado.

        Returns:
            Symbol | None: O símbolo correspondente, ou None.
        """
        found: Symbol | None = None
        for symbol in self._symbols:
            if symbol.addr <= addr:
                found = symbol
            else:
                break
        return found

    def __len__(self) -> int:
        return len(self._symbols)
