"""Adaptador do backend de debug: um processo `gdb` conectado ao stub do melonDS.

Usa o `gdb-multiarch` em linha de comando, com o limite de watchpoint de hardware
aplicado (para os watchpoints serem de hardware de verdade). A comunicação é por
stdin/stdout (binário) com `select`, para respeitar timeouts.
"""
import os
import re
import select
import signal
import subprocess
import tempfile
import threading
import time

from ..domain.ports import Debugger

_CORES = {"arm9", "arm7"}


class DebugError(RuntimeError):
    """Erro do backend de debug."""


class GdbBackend(Debugger):
    """Backend de debug via `gdb-multiarch` conectado ao stub do melonDS."""

    def __init__(self, gdb_path: str, arm9_port: int, arm7_port: int) -> None:
        """Guarda a configuração do backend.

        Parameters:
            gdb_path (str): Executável do gdb (ex.: ``gdb-multiarch``).
            arm9_port (int): Porta do stub do ARM9.
            arm7_port (int): Porta do stub do ARM7.
        """
        self._gdb_path = gdb_path
        self._ports = {"arm9": arm9_port, "arm7": arm7_port}
        self._proc: subprocess.Popen[bytes] | None = None
        self._core: str | None = None
        self._run_thread: threading.Thread | None = None
        self._run_output: str | None = None
        self._run_timeout: float = 3600.0

    def connect(self, core: str) -> None:
        """Conecta ao core escolhido, iniciando o gdb.

        Parameters:
            core (str): ``arm9`` ou ``arm7``.

        Raises:
            DebugError: Se o core for inválido ou o gdb não conectar.
        """
        if core not in _CORES:
            raise DebugError(f"core inválido: {core!r} (use 'arm9' ou 'arm7')")
        if self._proc is not None:
            self.close()
        self._run_thread = None
        self._run_output = None

        self._proc = subprocess.Popen(
            [self._gdb_path, "-q", "-nx"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            env={**os.environ, "LC_ALL": "C"},
        )
        self._read_until_prompt(timeout=10)
        self._cmd("set pagination off")
        self._cmd("set confirm off")
        self._cmd("set architecture arm")
        out = self._cmd(f"target remote 127.0.0.1:{self._ports[core]}", timeout=15)
        if "Remote debugging" not in out and "error" in out.lower():
            raise DebugError(f"falha ao conectar no stub: {out.strip()}")
        # deve ser setado APÓS o connect (o gdb reinicia isso ao conectar)
        self._cmd("set remote hardware-watchpoint-limit 4")
        self._core = core

    def read_register(self, name: str) -> int:
        """Lê um registrador pelo nome (ex.: ``pc``).

        Parameters:
            name (str): Nome do registrador.

        Returns:
            int: Valor do registrador.

        Raises:
            DebugError: Se não for possível ler.
        """
        out = self._cmd(f"p/x ${name}")
        match = re.search(r"\$\d+ = (0x[0-9a-fA-F]+)", out)
        if match is None:
            raise DebugError(f"não leu ${name}: {out.strip()}")
        return int(match.group(1), 16)

    def write_register(self, name: str, value: int) -> None:
        """Escreve um valor num registrador.

        Parameters:
            name (str): Nome do registrador.
            value (int): Valor a escrever.
        """
        self._cmd(f"set ${name} = 0x{value:x}")

    def read_memory(self, addr: int, size: int) -> bytes:
        """Lê ``size`` bytes da memória emulada em ``addr``.

        Parameters:
            addr (int): Endereço.
            size (int): Quantidade de bytes.

        Returns:
            bytes: Os bytes lidos.
        """
        path = self._temp_path()
        try:
            self._cmd(f"dump binary memory {path} 0x{addr:x} 0x{addr + size:x}")
            with open(path, "rb") as handle:
                return handle.read()
        finally:
            os.unlink(path)

    def write_memory(self, addr: int, data: bytes) -> None:
        """Escreve ``data`` na memória emulada a partir de ``addr``.

        Parameters:
            addr (int): Endereço.
            data (bytes): Bytes a escrever.
        """
        path = self._temp_path()
        try:
            with open(path, "wb") as handle:
                handle.write(data)
            self._cmd(f"restore {path} binary 0x{addr:x}")
        finally:
            os.unlink(path)

    def set_breakpoint(self, addr: int) -> int:
        """Cria um breakpoint de código em ``addr``.

        Parameters:
            addr (int): Endereço.

        Returns:
            int: Número do breakpoint.
        """
        out = self._cmd(f"break *0x{addr:x}")
        match = re.search(r"Breakpoint (\d+)", out)
        if match is None:
            raise DebugError(f"não criou breakpoint: {out.strip()}")
        return int(match.group(1))

    def set_watchpoint(self, addr: int, kind: str, condition: str | None = None) -> int:
        """Cria um watchpoint de hardware (``write``/``read``/``access``).

        Parameters:
            addr (int): Endereço vigiado.
            kind (str): Tipo de acesso.
            condition (str | None): Expressão gdb opcional (ex.:
                ``*(unsigned short*)0x0600F448 != 0``). O gdb só para quando a
                condição for verdadeira — útil para filtrar por valor.

        Returns:
            int: Número do watchpoint.

        Raises:
            DebugError: Se o tipo for inválido ou a criação falhar.
        """
        command = {"write": "watch", "read": "rwatch", "access": "awatch"}.get(kind)
        if command is None:
            raise DebugError(f"tipo de watchpoint inválido: {kind!r}")
        expr = f"{command} *(unsigned int*)0x{addr:x}"
        if condition:
            expr += f" if {condition}"
        out = self._cmd(expr)
        match = re.search(r"(?:Hardware watchpoint|Watchpoint) (\d+)", out)
        if match is None:
            raise DebugError(f"não criou watchpoint: {out.strip()}")
        return int(match.group(1))

    def remove(self, number: int) -> None:
        """Remove um breakpoint/watchpoint pelo número.

        Parameters:
            number (int): Número.
        """
        self._cmd(f"delete {number}")

    def continue_(self, timeout: float = 30.0) -> bool:
        """Retoma a execução e espera a parada.

        Parameters:
            timeout (float): Tempo máximo de espera em segundos.

        Returns:
            bool: True se parou; False se estourou o timeout (o alvo é interrompido).
        """
        out = self._cmd("continue", timeout=timeout)
        stopped = out.rstrip().endswith("(gdb)")
        if not stopped:
            self.interrupt()
        return stopped

    def step(self) -> None:
        """Executa uma instrução."""
        self._cmd("stepi", timeout=30)

    def is_running(self) -> bool:
        """True se há um `continue` de fundo em execução."""
        return self._run_thread is not None and self._run_thread.is_alive()

    def resume(self) -> None:
        """Retoma a execução em segundo plano (não bloqueia).

        Sobe uma thread que roda ``continue``; o alvo segue executando e o
        chamador pode injetar input (pelo canal de controle) enquanto isso.
        Use :meth:`wait_stop` para esperar a parada (breakpoint/watchpoint).
        """
        if self._proc is None or self._proc.stdin is None:
            raise DebugError("gdb não iniciado (chame connect antes)")
        if self.is_running():
            return
        self._run_output = None

        def _worker() -> None:
            try:
                self._run_output = self._cmd("continue", timeout=self._run_timeout)
            except Exception as exc:  # noqa: BLE001 - reportado ao chamador
                self._run_output = f"<erro: {exc}>"

        self._run_thread = threading.Thread(target=_worker, daemon=True)
        self._run_thread.start()

    def wait_stop(self, timeout: float) -> bool:
        """Espera o ``continue`` de fundo parar (ou estourar o timeout).

        Parameters:
            timeout (float): Tempo máximo de espera em segundos.

        Returns:
            bool: True se parou; False se ainda está rodando no prazo.
        """
        if self._run_thread is None:
            return True
        self._run_thread.join(timeout)
        if self._run_thread.is_alive():
            return False
        self._run_thread = None
        return True

    def interrupt(self) -> None:
        """Interrompe a execução (funciona com alvo parado ou rodando)."""
        if self._proc is None:
            return
        self._proc.send_signal(signal.SIGINT)
        if self._run_thread is not None and self.is_running():
            # deixa a thread do `continue` consumir a parada
            self._run_thread.join(10)
            self._run_thread = None
        else:
            self._read_until_prompt(timeout=10)

    def disconnect(self) -> None:
        """Desconecta do alvo (detach) — o emulador volta a rodar."""
        if self._proc is None:
            return
        if self.is_running():
            self.interrupt()
        self._cmd("detach", timeout=10)
        self.close()

    def close(self) -> None:
        """Encerra o gdb."""
        if self._proc is None:
            return
        if self._run_thread is not None and self._run_thread.is_alive():
            try:
                self._proc.send_signal(signal.SIGINT)
            except OSError:
                pass
            self._run_thread.join(5)
        self._run_thread = None
        try:
            if self._proc.stdin is not None:
                self._proc.stdin.write(b"quit\n")
                self._proc.stdin.flush()
        except (BrokenPipeError, ValueError):
            pass
        self._proc.wait(timeout=5)
        self._proc = None
        self._core = None

    def _cmd(self, text: str, timeout: float = 10) -> str:
        if self._proc is None or self._proc.stdin is None:
            raise DebugError("gdb não iniciado (chame connect antes)")
        if self.is_running() and threading.current_thread() is not self._run_thread:
            raise DebugError("alvo em execução: use debug_wait/debug_interrupt antes de outros comandos")
        self._proc.stdin.write((text + "\n").encode())
        self._proc.stdin.flush()
        return self._read_until_prompt(timeout)

    def _read_until_prompt(self, timeout: float) -> str:
        if self._proc is None or self._proc.stdout is None:
            raise DebugError("gdb não iniciado")
        fd = self._proc.stdout.fileno()
        buffer = ""
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                break
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk.decode(errors="replace")
            if buffer.rstrip().endswith("(gdb)"):
                break
        return buffer

    @staticmethod
    def _temp_path() -> str:
        handle, path = tempfile.mkstemp(prefix="re_mcp_")
        os.close(handle)
        return path
