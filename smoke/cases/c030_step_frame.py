"""Frame: step_frame works with the debugger attached and the frame is frozen (#11/#21)."""
from ..harness import Ctx, call, check, sha256

NAME = "frame: step_frame com debugger congela (#11/#21)"


async def run(ctx: Ctx) -> None:
    """With the debugger attached, step_frame advances N and stops (frame stable)."""
    async with ctx.session() as session:
        connect = await call(session, "debug_connect", core="arm9")
        check(connect.get("ok") is True, f"connect: {connect}")

        step = await call(session, "emu_step_frame", n=60)
        check(step.get("ok") is True and step.get("frames") == 60, f"step_frame: {step}")

        cap1 = await call(session, "screen_capture", screens="bottom")
        paths1 = cap1.get("paths") or []
        check(len(paths1) == 1, f"capture 1: {cap1}")
        hash1 = sha256(paths1[0])

        cap2 = await call(session, "screen_capture", screens="bottom")
        paths2 = cap2.get("paths") or []
        check(len(paths2) == 1, f"capture 2: {cap2}")
        hash2 = sha256(paths2[0])

        check(hash1 == hash2, "captura mudou com o debugger parado (não congelou)")

        await call(session, "debug_disconnect")
