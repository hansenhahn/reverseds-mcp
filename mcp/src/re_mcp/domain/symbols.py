"""Symbols: a map from addresses to names (value object, without I/O)."""
import json
import threading
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Symbol:
    """A symbol: a name for an address, optionally scoped to an overlay."""

    addr: int
    name: str
    kind: str = "label"
    comment: str | None = None
    overlay: int | None = None


class SymbolTable:
    """Thread-safe symbol table keyed by ``(addr, overlay)``."""

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
        """Add a symbol, replacing the same ``(addr, overlay)`` and ``(name, overlay)``.

        Symbols in other overlays are preserved, so the same address can carry
        different names in overlays that share a base.

        Parameters:
            symbol (Symbol): The symbol to add.
        """
        with self._lock:
            self._symbols = [
                current
                for current in self._symbols
                if not (
                    (current.addr == symbol.addr and current.overlay == symbol.overlay)
                    or (current.name == symbol.name and current.overlay == symbol.overlay)
                )
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

    def replace_overlay(self, overlay: int, other: "SymbolTable") -> None:
        """Replace only ``overlay``'s symbols with ``other`` (keeps the rest).

        Parameters:
            overlay (int): Overlay whose symbols are replaced.
            other (SymbolTable): The new symbols for that overlay.
        """
        with self._lock:
            self._symbols = [
                symbol for symbol in self._symbols if symbol.overlay != overlay
            ]
            for symbol in other.all():
                self.add(symbol)

    def candidates(self, addr: int, overlay: int | None = None) -> list[Symbol]:
        """Symbols at the nearest address ≤ ``addr``, optionally scoped to an overlay.

        With ``overlay``, symbols from that overlay and globals (``overlay=None``)
        are considered; a specific overlay wins over a global at the same address.
        Without ``overlay``, all symbols at the address are returned, which may be
        ambiguous when overlays share a base.

        Parameters:
            addr (int): The address to look up.
            overlay (int | None): Optional overlay filter.

        Returns:
            list[Symbol]: The matching symbols (empty if none).
        """
        with self._lock:
            eligible = [
                symbol
                for symbol in self._symbols
                if overlay is None
                or symbol.overlay == overlay
                or symbol.overlay is None
            ]
            max_addr: int | None = None
            for symbol in eligible:
                if symbol.addr <= addr and (max_addr is None or symbol.addr > max_addr):
                    max_addr = symbol.addr
            if max_addr is None:
                return []
            at_addr = [symbol for symbol in eligible if symbol.addr == max_addr]
            if overlay is not None:
                specific = [
                    symbol for symbol in at_addr if symbol.overlay == overlay
                ]
                if specific:
                    return specific
                return [symbol for symbol in at_addr if symbol.overlay is None]
            return at_addr

    def resolve(self, addr: int, overlay: int | None = None) -> Symbol | None:
        """The symbol at the nearest address ≤ ``addr``, or None when ambiguous.

        Parameters:
            addr (int): The address to look up.
            overlay (int | None): Optional overlay filter.

        Returns:
            Symbol | None: The single matching symbol, or None if there is none or
            more than one candidate at the nearest address.
        """
        candidates = self.candidates(addr, overlay)
        return candidates[0] if len(candidates) == 1 else None

    def by_name(self, name: str, overlay: int | None = None) -> Symbol | None:
        """Return the symbol with exactly ``name``, optionally filtered by overlay."""
        with self._lock:
            for symbol in self._symbols:
                if symbol.name != name:
                    continue
                if overlay is None or symbol.overlay in (overlay, None):
                    return symbol
            return None

    def all(self, overlay: int | None = None) -> list[Symbol]:
        """All symbols, ordered by address, optionally filtered by overlay.

        Parameters:
            overlay (int | None): When set, return only symbols from that overlay.

        Returns:
            list[Symbol]: The symbols.
        """
        with self._lock:
            if overlay is None:
                return list(self._symbols)
            return [
                symbol for symbol in self._symbols if symbol.overlay == overlay
            ]

    def __len__(self) -> int:
        with self._lock:
            return len(self._symbols)
