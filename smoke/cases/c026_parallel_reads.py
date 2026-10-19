"""GDB: concurrent register reads are serialized (no mixed responses)."""
import asyncio

from ..harness import Ctx, call, check

NAME = "gdb: parallel register reads are serialized"


async def run(ctx: Ctx) -> None:
    """Several register reads at once must all return the right value."""
    async with ctx.session() as session:
        connect = await call(session, "debug_connect", core="arm9")
        check(connect.get("ok") is True, f"connect: {connect}")

        names = ["pc", "sp", "lr", "r0", "r1", "r2", "r3"]
        results = await asyncio.gather(
            *(call(session, "debug_read_register", name=name) for name in names)
        )
        for name, result in zip(names, results):
            check("value" in result, f"read {name} falhou: {result}")

        after = await call(session, "debug_read_register", name="pc")
        check("value" in after, f"leitura após o burst falhou (gdb caiu?): {after}")
        await call(session, "debug_disconnect")
