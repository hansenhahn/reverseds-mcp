"""Control channel: the MCP reaches the emulator and reports health."""
from ..harness import Ctx, call, check

NAME = "control: ping + health_check"


async def run(ctx: Ctx) -> None:
    """The control channel answers ping and health_check sees it."""
    async with ctx.session() as session:
        pong = await call(session, "ping")
        check(pong.get("pong") is True, f"ping inesperado: {pong}")
        health = await call(session, "health_check")
        check(
            health.get("control", {}).get("pong") is True,
            f"health_check.control: {health}",
        )
