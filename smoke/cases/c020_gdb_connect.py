"""GDB: connect, read a register and disconnect."""
from ..harness import Ctx, call, check

NAME = "gdb: connect + read pc + disconnect"


async def run(ctx: Ctx) -> None:
    """A basic connect/read/disconnect round-trip works."""
    async with ctx.session() as session:
        connect = await call(session, "debug_connect", core="arm9")
        check(connect.get("ok") is True and "pc" in connect, f"connect: {connect}")

        pc = await call(session, "debug_read_register", name="pc")
        check("value" in pc, f"read pc: {pc}")

        disconnect = await call(session, "debug_disconnect")
        check(disconnect.get("ok") is True, f"disconnect: {disconnect}")
