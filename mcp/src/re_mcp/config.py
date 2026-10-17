"""Configuração do MCP (lida do ambiente)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Config:
    """Configuração do servidor MCP (endereços dos backends)."""

    control_socket: str
    gdb_path: str
    arm9_port: int
    arm7_port: int
    rom_path: str | None
    out_dir: str

    @classmethod
    def from_env(cls) -> "Config":
        """Lê a configuração das variáveis de ambiente.

        Returns:
            Config: A configuração com os defaults aplicados.
        """
        return cls(
            control_socket=os.environ.get(
                "RE_MCP_CONTROL_SOCKET", "/tmp/melonds-control.sock"
            ),
            gdb_path=os.environ.get("RE_MCP_GDB", "gdb-multiarch"),
            arm9_port=int(os.environ.get("RE_MCP_ARM9_PORT", "3333")),
            arm7_port=int(os.environ.get("RE_MCP_ARM7_PORT", "3334")),
            rom_path=os.environ.get("RE_MCP_ROM") or None,
            out_dir=os.environ.get("RE_MCP_OUT_DIR", "/tmp/re_mcp"),
        )

    def debug_port(self, core: str) -> int:
        """Devolve a porta do stub GDB para o core.

        Parameters:
            core (str): ``arm9`` ou ``arm7``.

        Returns:
            int: A porta correspondente.

        Raises:
            ValueError: Se o core for desconhecido.
        """
        if core == "arm9":
            return self.arm9_port
        if core == "arm7":
            return self.arm7_port
        raise ValueError(f"core desconhecido: {core!r} (use 'arm9' ou 'arm7')")
