"""Symbols: a map from addresses to names (value object, without I/O)."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Symbol:
    """A symbol: a name for an address."""

    addr: int
    name: str


class SymbolTable:
    """Symbol table ordered by address, with resolution by nearest symbol."""

    def __init__(self, symbols: list[Symbol]) -> None:
        self._symbols = sorted(symbols, key=lambda symbol: symbol.addr)

    @classmethod
    def from_map(cls, text: str) -> "SymbolTable":
        """Parse a symbol map (``address name`` per line).

        Parameters:
            text (str): The `.map` contents (lines ``0xADDR name`` or ``ADDR name``).

        Returns:
            SymbolTable: The symbol table.
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
        """The symbol containing ``addr`` (largest address ≤ ``addr``), or None.

        Parameters:
            addr (int): The address to look up.

        Returns:
            Symbol | None: The matching symbol, or None.
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
