"""Testes do domínio puro (`disasm`, macros de input) — sem emulador."""
import pytest

from re_mcp.domain.disasm import Disassembler
from re_mcp.domain.emulation import NO_KEY, InputMacros, InputStep


class FakeChannel:
    """Canal de controle fake: registra as chamadas."""

    def __init__(self, fail_on: int | None = None) -> None:
        self.calls: list[tuple[str, dict | None]] = []
        self._n = 0
        self._fail_on = fail_on

    def call(self, method: str, params: dict | None = None) -> dict:
        self._n += 1
        self.calls.append((method, params))
        if self._fail_on is not None and self._n == self._fail_on:
            raise RuntimeError("boom")
        return {}

    def read_message(self, timeout: float) -> dict | None:
        return None

    def close(self) -> None:
        pass


def test_disassemble_arm() -> None:
    """`mov r0, #1` (ARM) é desmontado como `mov`."""
    insns = Disassembler().disassemble(bytes.fromhex("0100a0e3"), 0x02000000, "arm", 1)
    assert insns[0].mnemonic == "mov"
    assert insns[0].address == 0x02000000


def test_disassemble_thumb() -> None:
    """`movs r0, #1` (Thumb) é desmontado como `movs`."""
    insns = Disassembler().disassemble(bytes.fromhex("0120"), 0x02000000, "thumb", 1)
    assert insns[0].mnemonic == "movs"


def test_disassemble_invalid_mode() -> None:
    """Modo inválido levanta ValueError."""
    with pytest.raises(ValueError):
        Disassembler().disassemble(b"\x00\x00\x00\x00", 0, "x86")


def test_tap_presses_and_releases() -> None:
    """`tap` aperta a máscara e solta no fim."""
    ch = FakeChannel()
    sleeps: list[float] = []
    InputMacros(ch, sleep=sleeps.append).tap(0xFF7, 100)
    assert ch.calls[0] == ("input.key", {"mask": 0xFF7})
    assert ch.calls[-1] == ("input.release", None)
    assert sleeps == [0.1]


def test_sequence_runs_steps() -> None:
    """`run` executa os passos e solta no fim."""
    ch = FakeChannel()
    steps = [InputStep(ms=100, after_ms=1000, mask=0xFF7), InputStep(ms=100, after_ms=0, mask=0xFFD)]
    InputMacros(ch, sleep=lambda _s: None).run(steps)
    assert ("input.key", {"mask": 0xFF7}) in ch.calls
    assert ("input.key", {"mask": 0xFFD}) in ch.calls
    assert ch.calls[-1] == ("input.release", None)


def test_sequence_wait_only_step() -> None:
    """Passo sem máscara apenas espera (não pressiona)."""
    ch = FakeChannel()
    InputMacros(ch, sleep=lambda _s: None).run([InputStep(ms=50, after_ms=0, mask=None)])
    assert all(method == "input.release" for method, _ in ch.calls)


def test_sequence_releases_on_error() -> None:
    """Se um passo falha, o input é solto mesmo assim."""
    ch = FakeChannel(fail_on=3)
    with pytest.raises(RuntimeError):
        InputMacros(ch, sleep=lambda _s: None).run(
            [InputStep(ms=100, mask=0xFF7), InputStep(ms=100, mask=0xFFD)]
        )
    assert ch.calls[-1] == ("input.release", None)


def test_sequence_rejects_too_long() -> None:
    """Sequência acima do teto levanta ValueError."""
    with pytest.raises(ValueError):
        InputMacros(FakeChannel(), sleep=lambda _s: None).run(
            [InputStep(ms=10_000, after_ms=10_000, mask=0xFF7)], max_total_ms=1000
        )


def test_no_key_constant() -> None:
    """A const de 'nada pressionado' é 0xFFF."""
    assert NO_KEY == 0xFFF
