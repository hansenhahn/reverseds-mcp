"""ARM9 address parsing and memory-region description (pure, no I/O)."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemoryRegion:
    """An inclusive address range of the ARM9 memory map."""

    name: str
    start: int
    end: int

    def covers(self, addr: int) -> bool:
        """Whether ``start <= addr <= end``.

        Parameters:
            addr (int): The address to test.

        Returns:
            bool: True when the address is inside the region.
        """
        return self.start <= addr <= self.end

    @property
    def size(self) -> int:
        """The region size in bytes."""
        return self.end - self.start + 1


NDS9_REGIONS: tuple[MemoryRegion, ...] = (
    MemoryRegion("itcm", 0x00000000, 0x00007FFF),
    MemoryRegion("dtcm", 0x00800000, 0x00803FFF),
    MemoryRegion("main-ram", 0x02000000, 0x023FFFFF),
    MemoryRegion("shared-wram", 0x03000000, 0x03007FFF),
    MemoryRegion("io", 0x04000000, 0x04FFFFFF),
    MemoryRegion("palettes", 0x05000000, 0x050007FF),
    MemoryRegion("vram-a-bg", 0x06000000, 0x061FFFFF),
    MemoryRegion("vram-b-bg", 0x06200000, 0x0621FFFF),
    MemoryRegion("vram-a-obj", 0x06400000, 0x065FFFFF),
    MemoryRegion("vram-b-obj", 0x06600000, 0x0661FFFF),
    MemoryRegion("vram-lcdc", 0x06800000, 0x068A3FFF),
    MemoryRegion("oam", 0x07000000, 0x070007FF),
    MemoryRegion("gba-rom", 0x08000000, 0x09FFFFFF),
    MemoryRegion("gba-ram", 0x0A000000, 0x0A00FFFF),
    MemoryRegion("arm9-bios", 0xFFFF0000, 0xFFFFFFFF),
)


@dataclass(frozen=True, slots=True)
class AddressInfo:
    """A normalized address and the region that contains it."""

    value: int
    region: MemoryRegion | None

    @property
    def value_hex(self) -> str:
        """The address as ``0x%08x``."""
        return f"0x{self.value:08x}"

    @property
    def aligned4(self) -> bool:
        """Whether the address is 4-byte aligned."""
        return self.value % 4 == 0

    @property
    def mapped(self) -> bool:
        """Whether the address belongs to a known ARM9 region."""
        return self.region is not None


class AddressSpace:
    """ARM9 address parsing and region resolution behavior."""

    regions: tuple[MemoryRegion, ...] = NDS9_REGIONS

    @classmethod
    def parse(cls, value: int | str) -> int:
        """Parse an address from an integer or text.

        Text accepts ``0x``-prefixed hex, bare hex (when it contains ``A-F``) or
        decimal. Underscores are ignored, as in Python literals.

        Parameters:
            value (int | str): The address as an integer or text.

        Returns:
            int: The address (0..0xFFFFFFFF).

        Raises:
            ValueError: If the value is invalid or out of range.
        """
        if isinstance(value, bool):
            raise ValueError("endereço inválido: booleano")
        if isinstance(value, int):
            addr = value
        elif isinstance(value, str):
            text = value.strip().replace("_", "")
            if not text:
                raise ValueError("endereço vazio")
            if text.lower().startswith("0x"):
                text = text[2:]
                base = 16
            elif any(char in "abcdefABCDEF" for char in text):
                base = 16
            else:
                base = 10
            try:
                addr = int(text, base)
            except ValueError:
                raise ValueError(f"endereço inválido: {value!r}") from None
        else:
            raise ValueError(f"endereço inválido: {value!r}")
        if not 0 <= addr <= 0xFFFFFFFF:
            raise ValueError(f"endereço fora de 0..0xFFFFFFFF: {value!r}")
        return addr

    @classmethod
    def region_for(cls, addr: int) -> MemoryRegion | None:
        """Return the ARM9 region containing ``addr``, if any.

        Parameters:
            addr (int): The address.

        Returns:
            MemoryRegion | None: The region, or None when it is not mapped.
        """
        for region in cls.regions:
            if region.covers(addr):
                return region
        return None

    @classmethod
    def describe(cls, addr: int) -> AddressInfo:
        """Normalize ``addr`` and resolve its ARM9 region.

        Parameters:
            addr (int): The address (already parsed).

        Returns:
            AddressInfo: The address with its region (or None).
        """
        return AddressInfo(addr, cls.region_for(addr))
