"""GDB: debug_connect while the target is running yields a usable session (#22 probe)."""
import asyncio

from ..harness import Ctx, call, check

NAME = "gdb: connect while target running (#22 probe)"


async def run(ctx: Ctx) -> None:
    """Re-connecting after debug_resume must return a halted, usable session."""
    async with ctx.session() as session:
        connect = await call(session, "debug_connect", core="arm9")
        check(connect.get("ok") is True, f"connect: {connect}")

        resume = await call(session, "debug_resume")
        check(resume.get("ok") is True, f"resume: {resume}")
        await asyncio.sleep(0.3)

        again = await call(session, "debug_connect", core="arm9")
        check(again.get("ok") is True, f"connect com alvo rodando falhou: {again}")

        await call(session, "debug_interrupt")
        await call(session, "debug_disconnect")
