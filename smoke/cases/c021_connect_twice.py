"""GDB: a second debug_connect to the same core is a no-op (regression #22)."""
from ..harness import Ctx, call, check

NAME = "gdb: debug_connect twice is idempotent (#22)"


async def run(ctx: Ctx) -> None:
    """Connecting twice to the same core must not time out."""
    async with ctx.session() as session:
        first = await call(session, "debug_connect", core="arm9")
        check(first.get("ok") is True, f"1st connect: {first}")

        second = await call(session, "debug_connect", core="arm9")
        check(
            second.get("ok") is True and "pc" in second,
            f"2nd connect (idempotent) falhou: {second}",
        )

        await call(session, "debug_disconnect")
