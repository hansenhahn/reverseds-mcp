"""Debug backend adapter: a `gdb` process connected to the melonDS stub.

Uses `gdb-multiarch` on the command line, with the hardware watchpoint limit applied
(so watchpoints are real hardware). Communication is over stdin/stdout (binary) with
`select`, to respect timeouts.
"""
import logging
import os
import re
import select
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import replace

from ..application.ports import Debugger
from ..domain.debug import Breakpoint, StackFrame

_CORES = {"arm9", "arm7"}
WATCHPOINT_LIMIT = 4
log = logging.getLogger("re_mcp.gdb")


class DebugError(RuntimeError):
    """Debug backend error."""


class GdbBackend(Debugger):
    """Debug backend via `gdb-multiarch` connected to the melonDS stub."""

    def __init__(self, gdb_path: str, arm9_port: int, arm7_port: int) -> None:
        """Store the backend configuration.

        Parameters:
            gdb_path (str): Path to the gdb executable (e.g. ``gdb-multiarch``).
            arm9_port (int): Port of the ARM9 stub.
            arm7_port (int): Port of the ARM7 stub.
        """
        self._gdb_path = gdb_path
        self._ports = {"arm9": arm9_port, "arm7": arm7_port}
        self._proc: subprocess.Popen[bytes] | None = None
        self._core: str | None = None
        self._run_thread: threading.Thread | None = None
        self._run_output: str | None = None
        self._run_timeout: float = 3600.0
        self._lock = threading.RLock()

    def connect(self, core: str) -> None:
        """Connect to the chosen core, starting gdb.

        Idempotent: if already connected to that core it returns the session in a
        usable (halted) state — stopping the target if it is running; switching
        cores detaches the current session cleanly before reconnecting.

        Parameters:
            core (str): ``arm9`` or ``arm7``.

        Raises:
            DebugError: If the core is invalid or gdb cannot connect.
        """
        if core not in _CORES:
            raise DebugError(f"core inválido: {core!r} (use 'arm9' ou 'arm7')")
        # Handle an existing session WITHOUT the lock: interrupt/disconnect may run
        # while a background `continue` holds the lock, so taking it here would block.
        if self._proc is not None:
            if self._proc.poll() is not None:
                with self._lock:
                    log.warning("gdb morto detectado no connect; descartando o handle")
                    self._proc = None
                    self._core = None
            elif self._core == core:
                if self.is_running():
                    self.interrupt()
                return
            else:
                try:
                    self.disconnect()
                except DebugError:
                    self.close()
        with self._lock:
            self._start(core)

    def _start(self, core: str) -> None:
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
        # must be set AFTER connect (gdb resets this on connect)
        self._cmd(f"set remote hardware-watchpoint-limit {WATCHPOINT_LIMIT}")
        self._core = core
        log.info("gdb conectado (core=%s, pid=%s)", core, getattr(self._proc, "pid", "?"))

    def core(self) -> str | None:
        """Return the connected core (``arm9``/``arm7``), if any."""
        return self._core

    def watchpoint_limit(self) -> int:
        """Return the configured hardware watchpoint limit."""
        return WATCHPOINT_LIMIT

    def refresh_registers(self) -> None:
        """Flush gdb's register cache (e.g. after a reset outside gdb)."""
        self._cmd("maintenance flush register-cache")

    def read_register(self, name: str) -> int:
        """Read a register by name (e.g. ``pc``).

        Parameters:
            name (str): Register name.

        Returns:
            int: The register value.

        Raises:
            DebugError: If it cannot read.
        """
        out = self._cmd(f"p/x ${name}")
        match = re.search(r"\$\d+ = (0x[0-9a-fA-F]+)", out)
        if match is None:
            raise DebugError(f"não leu ${name}: {out.strip()}")
        return int(match.group(1), 16)

    def write_register(self, name: str, value: int) -> None:
        """Write a value to a register.

        Parameters:
            name (str): Register name.
            value (int): Value to write.
        """
        self._cmd(f"set ${name} = 0x{value:x}")

    def read_memory(self, addr: int, size: int) -> bytes:
        """Read ``size`` bytes of emulated memory at ``addr``.

        Parameters:
            addr (int): Address.
            size (int): Number of bytes.

        Returns:
            bytes: The bytes read.

        Raises:
            DebugError: If the target is running or the dump is incomplete.
        """
        if self.is_running():
            raise DebugError(
                "alvo em execução: pare-o (debug_interrupt/debug_wait) antes de ler memória"
            )
        path = self._temp_path()
        try:
            self._cmd(f"dump binary memory {path} 0x{addr:x} 0x{addr + size:x}")
            with open(path, "rb") as handle:
                data = handle.read()
        finally:
            os.unlink(path)
        if len(data) != size:
            raise DebugError(
                f"leitura incompleta em 0x{addr:x}: esperado {size} byte(s), veio {len(data)}"
            )
        return data

    def write_memory(self, addr: int, data: bytes) -> None:
        """Write ``data`` to emulated memory starting at ``addr``.

        Parameters:
            addr (int): Address.
            data (bytes): Bytes to write.
        """
        path = self._temp_path()
        try:
            with open(path, "wb") as handle:
                handle.write(data)
            self._cmd(f"restore {path} binary 0x{addr:x}")
        finally:
            os.unlink(path)

    _GDB_ERROR_RE = re.compile(
        r"No symbol|Undefined command|Invalid|Cannot access memory|(?:^|\W)error(?:\W|$)",
        re.IGNORECASE,
    )

    @staticmethod
    def _validate_commands(commands: list[str]) -> None:
        """Reject commands that would break the gdb ``commands`` block."""
        for command in commands:
            if not command.strip():
                raise DebugError("comando vazio")
            if "\n" in command or "\r" in command:
                raise DebugError("cada comando deve ser uma única linha")
            if command.strip().lower() == "end":
                raise DebugError("'end' é reservado para fechar o bloco de comandos")

    def set_breakpoint(
        self,
        addr: int,
        condition: str | None = None,
        commands: list[str] | None = None,
    ) -> int:
        """Create a code breakpoint at ``addr``.

        Parameters:
            addr (int): Address.
            condition (str | None): Optional gdb expression; gdb only stops when true.
            commands (list[str] | None): Optional gdb commands run on the hit.

        Returns:
            int: The breakpoint number.

        Raises:
            DebugError: If creation or configuration fails (the breakpoint is removed).
        """
        out = self._cmd(f"break *0x{addr:x}")
        match = re.search(r"Breakpoint (\d+)", out)
        if match is None:
            raise DebugError(f"não criou breakpoint: {out.strip()}")
        number = int(match.group(1))
        try:
            if condition:
                cond_out = self._cmd(f"condition {number} {condition}")
                if self._GDB_ERROR_RE.search(cond_out):
                    raise DebugError(f"condição inválida: {cond_out.strip()}")
            if commands:
                self._validate_commands(commands)
                script = "\n".join(commands)
                cmd_out = self._cmd(f"commands {number}\n{script}\nend")
                if self._GDB_ERROR_RE.search(cmd_out):
                    raise DebugError(f"comandos inválidos: {cmd_out.strip()}")
        except DebugError:
            try:
                self.remove(number)
            except DebugError:
                pass
            raise
        return number

    def set_watchpoint(self, addr: int, kind: str, condition: str | None = None) -> int:
        """Create a hardware watchpoint (``write``/``read``/``access``).

        Parameters:
            addr (int): Watched address.
            kind (str): Access kind.
            condition (str | None): Optional gdb expression (e.g.
                ``*(unsigned short*)0x0600F448 != 0``). gdb only stops when the
                condition is true — useful to filter by value.

        Returns:
            int: The watchpoint number.

        Raises:
            DebugError: If the kind is invalid or creation fails.
        """
        command = {"write": "watch", "read": "rwatch", "access": "awatch"}.get(kind)
        if command is None:
            raise DebugError(f"tipo de watchpoint inválido: {kind!r}")
        expr = f"{command} *(unsigned int*)0x{addr:x}"
        if condition:
            expr += f" if {condition}"
        out = self._cmd(expr)
        match = re.search(
            r"(?:Hardware\s+(?:(?:read|access)(?:\s*\(read/write\))?\s+)?watchpoint"
            r"|Watchpoint)\s+(\d+)",
            out,
        )
        if match is None:
            raise DebugError(f"não criou watchpoint: {out.strip()}")
        return int(match.group(1))

    def remove(self, number: int) -> None:
        """Remove a breakpoint/watchpoint by number.

        Parameters:
            number (int): The number.

        Raises:
            DebugError: If gdb reports that the breakpoint does not exist.
        """
        out = self._cmd(f"delete {number}")
        if re.search(r"No breakpoint|not found", out, re.IGNORECASE):
            raise DebugError(f"breakpoint/watchpoint {number} não existe")

    _BT_RE = re.compile(r"^#(\d+)\s+0x([0-9a-fA-F]+)\s+in\s+(\S+)", re.MULTILINE)
    _BP_RE = re.compile(r"^(\d+)\s+(.+?)\s+(keep|del|dis)\s+([yn])\s*(.*)$")

    @staticmethod
    def _breakpoint_kind(type_text: str) -> str:
        """Normalize the gdb ``Type`` column into a stable kind."""
        normalized = " ".join(type_text.lower().split())
        if "breakpoint" in normalized or "watchpoint" not in normalized:
            return "breakpoint"
        if "read" in normalized:
            return "read-watchpoint"
        if "acc" in normalized:
            return "access-watchpoint"
        return "watchpoint"

    @staticmethod
    def _is_hardware(type_text: str) -> bool:
        """Whether the gdb ``Type`` column denotes a hardware resource.

        gdb omits the ``hw`` prefix for read/access watchpoints even when they use
        hardware; a plain ``watchpoint`` is the software fallback.
        """
        normalized = " ".join(type_text.lower().split())
        return "hw" in normalized.split() or "read" in normalized or "acc" in normalized

    def backtrace(self) -> list[StackFrame]:
        """Return the call stack of the connected core (innermost frame first)."""
        out = self._cmd("bt")
        frames: list[StackFrame] = []
        for match in self._BT_RE.finditer(out):
            function = match.group(3)
            frames.append(
                StackFrame(
                    index=int(match.group(1)),
                    pc=int(match.group(2), 16),
                    function=None if function == "??" else function,
                )
            )
        return frames

    def breakpoints(self) -> list[Breakpoint]:
        """Return the breakpoints/watchpoints known to the stub."""
        out = self._cmd("info breakpoints")
        result: list[Breakpoint] = []
        for line in out.splitlines():
            match = self._BP_RE.match(line.strip())
            if match is not None:
                rest = match.group(5)
                found = re.search(r"0x[0-9a-fA-F]+", rest)
                result.append(
                    Breakpoint(
                        number=int(match.group(1)),
                        kind=self._breakpoint_kind(match.group(2)),
                        address=int(found.group(0), 16) if found else None,
                        condition=None,
                        enabled=match.group(4) == "y",
                        hardware=self._is_hardware(match.group(2)),
                    )
                )
            elif result and "stop only if" in line:
                result[-1] = replace(result[-1], condition=line.split("stop only if", 1)[1].strip())
        return result

    def continue_(self, timeout: float = 30.0) -> bool:
        """Resume execution and wait for the stop.

        Parameters:
            timeout (float): Maximum wait time in seconds.

        Returns:
            bool: True if it stopped; False on timeout (the target is interrupted).
        """
        out = self._cmd("continue", timeout=timeout)
        stopped = out.rstrip().endswith("(gdb)")
        if not stopped:
            self.interrupt()
        return stopped

    def step(self) -> None:
        """Execute one instruction."""
        self._cmd("stepi", timeout=30)

    def is_running(self) -> bool:
        """True if a background `continue` is running."""
        return self._run_thread is not None and self._run_thread.is_alive()

    def resume(self) -> None:
        """Resume execution in the background (non-blocking).

        Spawns a thread that runs ``continue``; the target keeps executing and the
        caller can inject input (through the control channel) meanwhile.
        Use :meth:`wait_stop` to wait for the stop (breakpoint/watchpoint).
        """
        if self._proc is None or self._proc.stdin is None:
            raise DebugError("gdb não iniciado (chame connect antes)")
        if self.is_running():
            return
        self._run_output = None

        def _worker() -> None:
            try:
                self._run_output = self._cmd("continue", timeout=self._run_timeout)
            except Exception as exc:  # noqa: BLE001 - reported to the caller
                self._run_output = f"<erro: {exc}>"

        self._run_thread = threading.Thread(target=_worker, daemon=True)
        self._run_thread.start()

    def wait_stop(self, timeout: float) -> bool:
        """Wait for the background ``continue`` to stop (or time out).

        Parameters:
            timeout (float): Maximum wait time in seconds.

        Returns:
            bool: True if it stopped; False if still running in time.
        """
        if self._run_thread is None:
            return True
        self._run_thread.join(timeout)
        if self._run_thread.is_alive():
            return False
        self._run_thread = None
        return True

    def interrupt(self) -> None:
        """Interrupt execution (works with the target stopped or running)."""
        if self._proc is None:
            return
        self._proc.send_signal(signal.SIGINT)
        if self._run_thread is not None and self.is_running():
            # let the `continue` thread consume the stop
            self._run_thread.join(10)
            # only clear the handle if the thread actually finished; otherwise keep
            # it so `is_running()` stays True and other commands raise (instead of
            # blocking on the lock held by the still-running continue)
            if not self._run_thread.is_alive():
                self._run_thread = None
        else:
            self._read_until_prompt(timeout=10)

    def disconnect(self) -> None:
        """Disconnect from the target (detach) — the emulator runs again."""
        if self._proc is None:
            return
        if self.is_running():
            self.interrupt()
        try:
            self._cmd("detach", timeout=10)
        except DebugError:
            pass
        self.close()
        log.info("gdb desconectado")

    def close(self) -> None:
        """Shut down gdb."""
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
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=5)
        self._proc = None
        self._core = None

    def _cmd(self, text: str, timeout: float = 10) -> str:
        if self._proc is None or self._proc.stdin is None:
            raise DebugError("gdb não iniciado (chame connect antes)")
        if self.is_running() and threading.current_thread() is not self._run_thread:
            raise DebugError("alvo em execução: use debug_wait/debug_interrupt antes de outros comandos")
        with self._lock:
            self._ensure_alive()
            try:
                assert self._proc.stdin is not None
                self._proc.stdin.write((text + "\n").encode())
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError, ValueError) as exc:
                self._mark_dead()
                raise DebugError("gdb caiu; reconecte (debug_disconnect/debug_connect)") from exc
            out = self._read_until_prompt(timeout)
        if not out and self._proc is not None and self._proc.poll() is not None:
            self._mark_dead()
            raise DebugError("gdb caiu; reconecte (debug_disconnect/debug_connect)")
        return out

    def _ensure_alive(self) -> None:
        """Raise if the gdb process is gone."""
        if self._proc is None:
            raise DebugError("gdb não iniciado (chame connect antes)")
        if self._proc.poll() is not None:
            self._mark_dead()
            raise DebugError("gdb caiu; reconecte (debug_disconnect/debug_connect)")

    def _mark_dead(self) -> None:
        """Drop the dead gdb handle so the next call reconnects."""
        log.warning("gdb caiu; marcando desconectado")
        if self._proc is not None:
            try:
                self._proc.kill()
            except OSError:
                pass
        self._proc = None
        self._core = None
        self._run_thread = None

    def _read_until_prompt(self, timeout: float) -> str:
        if self._proc is None or self._proc.stdout is None:
            raise DebugError("gdb não iniciado")
        with self._lock:
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
