"""Patch model: writes, merged regions and byte-level equivalence (pure)."""
from dataclasses import dataclass

_MAX_WRITES = 256
_MAX_BYTES = 0x10000


@dataclass(frozen=True, slots=True)
class PatchWrite:
    """One ``{addr, bytes}`` write."""

    addr: int
    data: bytes

    @classmethod
    def from_spec(cls, spec: dict) -> "PatchWrite":
        """Build a write from a tool spec, validating the fields."""
        if not isinstance(spec, dict):
            raise ValueError("cada escrita deve ser um objeto {addr, bytes}")
        addr = spec.get("addr")
        raw = spec.get("bytes")
        if isinstance(addr, bool) or not isinstance(addr, int):
            raise ValueError(f"addr inválido: {addr!r}")
        if not 0 <= addr <= 0xFFFFFFFF:
            raise ValueError(f"addr fora de 0..0xFFFFFFFF: {addr!r}")
        if isinstance(raw, str):
            try:
                data = bytes.fromhex(raw)
            except ValueError:
                raise ValueError(f"bytes hex inválidos em 0x{addr:08x}") from None
        elif isinstance(raw, (bytes, bytearray)):
            data = bytes(raw)
        else:
            raise ValueError(f"bytes devem ser hex em 0x{addr:08x}")
        if not data:
            raise ValueError(f"escrita vazia em 0x{addr:08x}")
        if addr + len(data) > 0x100000000:
            raise ValueError(f"escrita passa de 0xFFFFFFFF em 0x{addr:08x}")
        return cls(addr, data)

    @property
    def end(self) -> int:
        """Exclusive end address."""
        return self.addr + len(self.data)


@dataclass(frozen=True, slots=True)
class Patch:
    """An ordered list of writes; later writes win on overlap."""

    writes: tuple[PatchWrite, ...]

    @classmethod
    def from_specs(cls, specs: list[dict]) -> "Patch":
        """Build a patch from ``[{addr, bytes}, ...]``."""
        if not isinstance(specs, list) or not specs:
            raise ValueError("patch vazio: informe ao menos uma escrita")
        if len(specs) > _MAX_WRITES:
            raise ValueError(f"patch com mais de {_MAX_WRITES} escritas")
        writes = tuple(PatchWrite.from_spec(spec) for spec in specs)
        if sum(len(write.data) for write in writes) > _MAX_BYTES:
            raise ValueError(f"patch maior que {_MAX_BYTES} bytes")
        return cls(writes)

    @property
    def regions(self) -> tuple[tuple[int, int], ...]:
        """Merged half-open address ranges touched by this patch."""
        return self._merge(self.writes)

    @classmethod
    def merged_regions(cls, *patches: "Patch") -> tuple[tuple[int, int], ...]:
        """Merged ranges of several patches (for a single memory read pass)."""
        writes = tuple(write for patch in patches for write in patch.writes)
        return cls._merge(writes)

    @staticmethod
    def _merge(writes: tuple[PatchWrite, ...]) -> tuple[tuple[int, int], ...]:
        if not writes:
            return ()
        spans = sorted((write.addr, write.end) for write in writes)
        merged: list[tuple[int, int]] = [spans[0]]
        for start, end in spans[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
        return tuple(merged)

    def touched(self) -> tuple[int, ...]:
        """Every address written by this patch."""
        return tuple(
            sorted({write.addr + offset for write in self.writes for offset in range(len(write.data))})
        )

    def apply(self, memory: dict[int, int]) -> dict[int, int]:
        """Apply the writes over a copy of ``memory`` and return the result."""
        result = dict(memory)
        for write in self.writes:
            for offset, byte in enumerate(write.data):
                result[write.addr + offset] = byte
        return result


@dataclass(frozen=True, slots=True)
class PatchByteDiff:
    """One byte that differs (or is missing on one side)."""

    addr: int
    asm: int | None
    c: int | None


@dataclass(frozen=True, slots=True)
class PatchDiff:
    """Byte-level comparison of two patches applied to the same memory."""

    diffs: tuple[PatchByteDiff, ...]

    @classmethod
    def between(
        cls, asm: Patch, c_equiv: Patch, memory: dict[int, int]
    ) -> "PatchDiff":
        """Apply both patches to ``memory`` and compare the touched bytes."""
        asm_result = asm.apply(memory)
        c_result = c_equiv.apply(memory)
        addresses = sorted(set(asm.touched()) | set(c_equiv.touched()))
        return cls(
            tuple(
                PatchByteDiff(addr, asm_result.get(addr), c_result.get(addr))
                for addr in addresses
                if asm_result.get(addr) != c_result.get(addr)
            )
        )

    @property
    def iguais(self) -> bool:
        """Whether both patches produce the same bytes."""
        return not self.diffs
