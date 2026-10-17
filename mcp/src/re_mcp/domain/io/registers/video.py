"""Video register definitions: DISPCNT, BGxCNT, DISP3DCNT, MASTER_BRIGHT."""
from ..decode import Register
from ._fields import bit, bits


def video_registers() -> list[Register]:
    """The video registers of engines A and B.

    Returns:
        list[Register]: DISPCNT, BG0-3CNT (A/B), DISP3DCNT and MASTER_BRIGHT (A/B).
    """
    dispcnt = (
        bits("bg_mode", 0, 2, tuple((m, f"mode {m}") for m in range(6))),
        bit("frame", 4, ((0, "frame 0"), (1, "frame 1"))),
        bit("hblank_oam", 5),
        bit("obj_1d_mapping", 6),
        bit("forced_blank", 7),
        bit("bg0_enable", 8),
        bit("bg1_enable", 9),
        bit("bg2_enable", 10),
        bit("bg3_enable", 11),
        bit("obj_enable", 12),
        bit("win0_enable", 13),
        bit("win1_enable", 14),
        bit("obj_win_enable", 15),
        bits(
            "display_mode",
            16,
            17,
            ((0, "display off"), (1, "graphics"), (2, "reserved"), (3, "main memory")),
        ),
    )
    bgcnt = (
        bits("priority", 0, 1, ((0, "highest"), (3, "lowest"))),
        bits("char_base", 2, 3),
        bit("mosaic", 6),
        bit("colors", 7, ((0, "16/16"), (1, "256/1"))),
        bits("screen_base", 8, 12),
        bit("area_overflow", 13, ((0, "transparent"), (1, "wrap"))),
        bits("screen_size", 14, 15),
    )
    disp3dcnt = (
        bit("texture_mapping", 0),
        bit("shading", 1, ((0, "toon"), (1, "highlight"))),
        bit("alpha_test", 2),
        bit("alpha_blending", 3),
        bit("anti_aliasing", 4),
        bit("edge_marking", 5),
        bit("fog_alpha_only", 6),
        bit("fog_enable", 7),
        bits("fog_shift", 8, 11),
        bit("rdlines_underflow", 12),
        bit("poly_overflow", 13),
        bit("rear_plane", 14, ((0, "blank"), (1, "bitmap"))),
    )
    master_bright = (
        bits("factor", 0, 4),
        bits(
            "mode",
            14,
            15,
            ((0, "disable"), (1, "up"), (2, "down"), (3, "reserved")),
        ),
    )
    registers = [
        Register("DISPCNT_A", 0x04000000, 4, dispcnt),
        Register("DISPCNT_B", 0x04001000, 4, dispcnt),
        Register("DISP3DCNT", 0x04000060, 4, disp3dcnt),
        Register("MASTER_BRIGHT_A", 0x0400006C, 2, master_bright),
        Register("MASTER_BRIGHT_B", 0x0400106C, 2, master_bright),
    ]
    for i in range(4):
        registers.append(Register(f"BG{i}CNT_A", 0x04000008 + 2 * i, 2, bgcnt))
        registers.append(Register(f"BG{i}CNT_B", 0x04001008 + 2 * i, 2, bgcnt))
    return registers
