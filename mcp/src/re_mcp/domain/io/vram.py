"""VRAM bank→window layout, following GBATEK's "VRAM Bank Control" table (pure)."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VramBinding:
    """How a VRAM bank is mapped: the target window and, when CPU-visible, its address."""

    bank: str
    mst: int
    offset: int
    target: str
    address: int | None


@dataclass(frozen=True, slots=True)
class VramCnt:
    """A VRAMCNT bank value: its enable/MST/offset and how the bank maps."""

    bank: str
    value: int

    @property
    def enabled(self) -> bool:
        """Whether the bank is enabled (bit 7)."""
        return bool(self.value & 0x80)

    @property
    def mst(self) -> int:
        """The mapping mode (bits 0-2)."""
        return self.value & 0x07

    @property
    def offset(self) -> int:
        """The bank offset (bits 3-4)."""
        return (self.value >> 3) & 0x03

    def binding(self) -> VramBinding | None:
        """The bank→window binding, or None if this bank/mode has no mapping."""
        resolved = self._resolve()
        if resolved is None:
            return None
        target, address = resolved
        return VramBinding(self.bank, self.mst, self.offset, target, address)

    def _resolve(self) -> tuple[str, int | None] | None:
        if self.mst == 0:
            return self._lcdc()
        if self.mst == 1:
            return self._engine_a_bg()
        if self.mst == 2:
            return self._engine_a_obj()
        if self.mst == 3:
            return self._texture()
        if self.mst == 4:
            return self._engine_b()
        if self.mst == 5 and self.bank in "FG":
            return "engine_a_obj_extpal", None
        return None

    def _lcdc(self) -> tuple[str, int]:
        index = "ABCD".find(self.bank)
        if index >= 0:
            return "lcdc", 0x6800000 + index * 0x20000
        if self.bank == "E":
            return "lcdc", 0x6880000
        fixed = {"F": 0x6890000, "G": 0x6894000, "H": 0x6898000, "I": 0x68A0000}
        return "lcdc", fixed[self.bank]

    def _engine_a_bg(self) -> tuple[str, int | None] | None:
        if self.bank in "ABCD":
            return "engine_a_bg", 0x6000000 + 0x20000 * self.offset
        if self.bank == "E":
            return "engine_a_bg", 0x6000000
        if self.bank in "FG":
            return "engine_a_bg", self._small_window(0x6000000)
        if self.bank == "H":
            return "engine_b_bg", 0x6200000
        if self.bank == "I":
            return "engine_b_bg", 0x6208000
        return None

    def _engine_a_obj(self) -> tuple[str, int | None] | None:
        if self.bank in "AB":
            return "engine_a_obj", 0x6400000 + 0x20000 * (self.offset & 1)
        if self.bank == "E":
            return "engine_a_obj", 0x6400000
        if self.bank in "FG":
            return "engine_a_obj", self._small_window(0x6400000)
        if self.bank in "CD":
            return "arm7_plain", 0x6000000 + 0x20000 * (self.offset & 1)
        if self.bank == "H":
            return "engine_b_bg_extpal", None
        if self.bank == "I":
            return "engine_b_obj", 0x6600000
        return None

    def _texture(self) -> tuple[str, int | None] | None:
        if self.bank in "ABCD":
            return f"texture_image_slot{self.offset}", None
        if self.bank in "EFG":
            return "texture_palette", None
        if self.bank == "I":
            return "engine_b_obj_extpal", None
        return None

    def _engine_b(self) -> tuple[str, int | None] | None:
        if self.bank == "C":
            return "engine_b_bg", 0x6200000
        if self.bank == "D":
            return "engine_b_obj", 0x6600000
        if self.bank in "EFG":
            return "engine_a_bg_extpal", None
        return None

    def _small_window(self, base: int) -> int:
        return base + 0x4000 * (self.offset & 1) + 0x10000 * ((self.offset >> 1) & 1)


@dataclass(frozen=True, slots=True)
class VramLayout:
    """The VRAM bank layout, resolved from the VRAMCNT values."""

    banks: tuple[VramCnt, ...]

    @classmethod
    def from_vramcnt(cls, values: dict[str, int]) -> "VramLayout":
        """Build the layout from the VRAMCNT byte values, keyed by bank letter.

        Parameters:
            values (dict[str, int]): The ``VRAMCNT_A..I`` byte values.

        Returns:
            VramLayout: The layout.
        """
        return cls(tuple(VramCnt(bank, values.get(bank, 0)) for bank in "ABCDEFGHI"))

    def bindings(self) -> list[VramBinding]:
        """The bindings of the enabled, mapped banks (disabled/unmapped omitted).

        Returns:
            list[VramBinding]: The active bindings.
        """
        out: list[VramBinding] = []
        for bank in self.banks:
            if not bank.enabled:
                continue
            binding = bank.binding()
            if binding is not None:
                out.append(binding)
        return out
