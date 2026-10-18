"""GDB: switching cores detaches the current session and connects the other (regression #22)."""
from ..harness import Ctx, call, check

NAME = "gdb: switch core arm9 -> arm7 (#22)"


async def run(ctx: Ctx) -> None:
    """Reconnecting to a different core must succeed."""
    async with ctx.session() as session:
        arm9 = await call(session, "debug_connect", core="arm9")
        check(arm9.get("ok") is True, f"arm9: {arm9}")

        arm7 = await call(session, "debug_connect", core="arm7")
        check(
            arm7.get("ok") is True and arm7.get("core") == "arm7",
            f"arm7: {arm7}",
        )

        await call(session, "debug_disconnect")
