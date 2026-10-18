"""Tools: the control-channel pause tools are gone (regression #11/#21)."""
from ..harness import Ctx, check, tool_names

NAME = "tools: emu_pause/emu_resume ausentes (#21)"


async def run(ctx: Ctx) -> None:
    """step_frame replaces the pause/resume tools."""
    async with ctx.session() as session:
        names = await tool_names(session)
        check("emu_pause" not in names, "emu_pause ainda exposto")
        check("emu_resume" not in names, "emu_resume ainda exposto")
        check("emu_step_frame" in names, "emu_step_frame ausente")
