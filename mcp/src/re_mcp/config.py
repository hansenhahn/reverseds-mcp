"""MCP configuration (read from the environment)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Config:
    """MCP server configuration (backend addresses)."""

    control_socket: str
    gdb_path: str
    arm9_port: int
    arm7_port: int
    rom_path: str | None
    out_dir: str

    @classmethod
    def from_env(cls) -> "Config":
        """Read the configuration from the environment variables.

        Returns:
            Config: The configuration with defaults applied.
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
        """Return the GDB stub port for the core.

        Parameters:
            core (str): ``arm9`` or ``arm7``.

        Returns:
            int: The corresponding port.

        Raises:
            ValueError: If the core is unknown.
        """
        if core == "arm9":
            return self.arm9_port
        if core == "arm7":
            return self.arm7_port
        raise ValueError(f"core desconhecido: {core!r} (use 'arm9' ou 'arm7')")
