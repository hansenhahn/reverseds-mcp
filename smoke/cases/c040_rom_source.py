"""ROM source of truth: the cart tools read the ROM loaded in the emulator."""
from pathlib import Path

from ..harness import Ctx, call, check

NAME = "rom: emulator ROM drives rom_info/cart/overlays"


async def run(ctx: Ctx) -> None:
    """rom_info matches the opened ROM and cart/overlay tools use it."""
    async with ctx.session() as session:
        info = await call(session, "rom_info")
        check(info.get("loaded") is True, f"rom_info: {info}")
        check(info.get("name") == ctx.rom.name, f"ROM errada: {info}")
        check(
            int(info.get("size", 0)) >= ctx.rom.stat().st_size,
            f"tamanho inesperado: {info}",
        )

        listing = await call(session, "cart_list")
        check("error" not in listing, f"cart_list: {listing}")
        files = listing.get("files", [])
        check(int(listing.get("total", 0)) > 0, f"cart_list vazio: {listing}")

        path = min((entry["path"] for entry in files), key=len)
        read = await call(session, "cart_read", path=path)
        check("error" not in read, f"cart_read({path}): {read}")
        check(int(read.get("size", 0)) > 0, f"cart_read({path}): {read}")
        check(Path(read["path"]).is_file(), f"arquivo não gravado: {read}")

        overlays = await call(session, "overlay_list")
        check("error" not in overlays, f"overlay_list: {overlays}")
        check("arm9" in overlays and "arm7" in overlays, f"overlay_list: {overlays}")
