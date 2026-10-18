"""GDB: ending a session and starting another connects cleanly (handoff)."""
from ..harness import Ctx, call, check

NAME = "gdb: session handoff (connect, disconnect, connect)"


async def run(ctx: Ctx) -> None:
    """A new session connects fine after the previous one disconnected."""
    async with ctx.session() as first:
        a = await call(first, "debug_connect", core="arm9")
        check(a.get("ok") is True, f"1st session connect: {a}")
        await call(first, "debug_disconnect")

    async with ctx.session() as second:
        b = await call(second, "debug_connect", core="arm9")
        check(b.get("ok") is True and "pc" in b, f"2nd session connect: {b}")
        await call(second, "debug_disconnect")
