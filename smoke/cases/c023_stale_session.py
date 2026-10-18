"""GDB: a new connection replaces a stale session (regression #12)."""
from ..harness import Ctx, call, check

NAME = "gdb: stale session replaced by a new connection (#12)"


async def run(ctx: Ctx) -> None:
    """A second debugger must be served while the first is still connected."""
    async with ctx.session() as session_a:
        a = await call(session_a, "debug_connect", core="arm9")
        check(a.get("ok") is True, f"A connect: {a}")

        async with ctx.session() as session_b:
            b = await call(session_b, "debug_connect", core="arm9")
            check(b.get("ok") is True and "pc" in b, f"B connect (replace): {b}")
            await call(session_b, "debug_disconnect")

        await call(session_a, "debug_disconnect")
