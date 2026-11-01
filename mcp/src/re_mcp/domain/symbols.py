"""Symbols: a map from addresses to names (value object, without I/O)."""
import json
import threading
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Symbol:
    """A symbol: a name for an address, with optional model metadata."""

    addr: int
    name: str
    kind: str = "label"
    comment: str | None = None
    overlay: int | None = None


class SymbolTable:
    """Thread-safe symbol table ordered by address, with nearest resolution."""

    def __init__(self, symbols: list[Symbol]) -> None:
        self._lock = threading.RLock()
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

    @classmethod
    def from_json(cls, text: str) -> "SymbolTable":
        """Parse the persisted symbol table.

        Parameters:
            text (str): The JSON contents.

        Returns:
            SymbolTable: The symbol table.

        Raises:
            ValueError: If the JSON is invalid or has the wrong shape.
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON de símbolos inválido: {exc}") from exc
        raw = data.get("symbols")
        if not isinstance(raw, list):
            raise ValueError("JSON de símbolos sem a lista 'symbols'")
        symbols: list[Symbol] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                symbols.append(
                    Symbol(
                        addr=int(item["addr"]),
                        name=str(item["name"]),
                        kind=str(item.get("kind") or "label"),
                        comment=item.get("comment"),
                        overlay=item.get("overlay"),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return cls(symbols)

    def to_json(self) -> str:
        """Serialize the table to JSON."""
        with self._lock:
            data = {
                "symbols": [
                    {
                        "addr": symbol.addr,
                        "name": symbol.name,
                        "kind": symbol.kind,
                        "comment": symbol.comment,
                        "overlay": symbol.overlay,
                    }
                    for symbol in self._symbols
                ]
            }
        return json.dumps(data, indent=2)

    def add(self, symbol: Symbol) -> None:
        """Add a symbol, replacing the same address and removing the same name.

        Parameters:
            symbol (Symbol): The symbol to add.
        """
        with self._lock:
            self._symbols = [
                current
                for current in self._symbols
                if current.addr != symbol.addr and current.name != symbol.name
            ]
            self._symbols.append(symbol)
            self._symbols.sort(key=lambda item: item.addr)

    def merge(self, other: "SymbolTable") -> None:
        """Merge another table into this one (other wins on conflicts).

        Parameters:
            other (SymbolTable): The table to merge.
        """
        for symbol in other.all():
            self.add(symbol)

    def resolve(self, addr: int) -> Symbol | None:
        """The symbol containing ``addr`` (largest address ≤ ``addr``), or None.

        Parameters:
            addr (int): The address to look up.

        Returns:
            Symbol | None: The matching symbol, or None.
        """
        with self._lock:
            found: Symbol | None = None
            for symbol in self._symbols:
                if symbol.addr <= addr:
                    found = symbol
                else:
                    break
            return found

    def by_name(self, name: str) -> Symbol | None:
        """Return the symbol with exactly ``name``, if any."""
        with self._lock:
            for symbol in self._symbols:
                if symbol.name == name:
                    return symbol
            return None

    def all(self) -> list[Symbol]:
        """All symbols, ordered by address."""
        with self._lock:
            return list(self._symbols)

    def __len__(self) -> int:
        with self._lock:
            return len(self._symbols)
