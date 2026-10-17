"""Video register definitions: DISPCNT, BGxCNT, DISP3DCNT, MASTER_BRIGHT."""
from ..decode import Register, RegField


def video_registers() -> list[Register]:
    """The video registers of engines A and B.

    Returns:
        list[Register]: DISPCNT, BG0-3CNT (A/B), DISP3DCNT and MASTER_BRIGHT (A/B).
    """
    dispcnt = (
        RegField.bits("bg_mode", 0, 2, tuple((m, f"mode {m}") for m in range(6)),
                      "BG mode (0-5 = video modes; 6-7 prohibited)"),
        RegField.bit("frame", 4, ((0, "frame 0"), (1, "frame 1")),
                     "Display frame select (BG modes 4,5 only)"),
        RegField.bit("hblank_oam", 5, (), "Allow OAM access during H-blank"),
        RegField.bit("obj_1d_mapping", 6, (), "OBJ tile VRAM mapping (0=2D, 1=1D)"),
        RegField.bit("forced_blank", 7, (), "Forced blank (white lines; fast VRAM/palette/OAM access)"),
        RegField.bit("bg0_enable", 8, (), "Screen display BG0"),
        RegField.bit("bg1_enable", 9, (), "Screen display BG1"),
        RegField.bit("bg2_enable", 10, (), "Screen display BG2"),
        RegField.bit("bg3_enable", 11, (), "Screen display BG3"),
        RegField.bit("obj_enable", 12, (), "Screen display OBJ"),
        RegField.bit("win0_enable", 13, (), "Window 0 display flag"),
        RegField.bit("win1_enable", 14, (), "Window 1 display flag"),
        RegField.bit("obj_win_enable", 15, (), "OBJ window display flag"),
        RegField.bits("display_mode", 16, 17,
                      ((0, "display off"), (1, "graphics"), (2, "reserved"), (3, "main memory")),
                      "Display mode"),
    )
    bgcnt = (
        RegField.bits("priority", 0, 1, ((0, "highest"), (3, "lowest")), "BG priority"),
        RegField.bits("char_base", 2, 3, (), "Character base block (16 KB units)"),
        RegField.bit("mosaic", 6, (), "Mosaic"),
        RegField.bit("colors", 7, ((0, "16/16"), (1, "256/1")), "Colors/palettes"),
        RegField.bits("screen_base", 8, 12, (), "Screen base block (2 KB units)"),
        RegField.bit("area_overflow", 13, ((0, "transparent"), (1, "wrap")),
                     "Display area overflow (BG2/BG3)"),
        RegField.bits("screen_size", 14, 15, (), "Screen size"),
    )
    disp3dcnt = (
        RegField.bit("texture_mapping", 0, (), "Texture mapping"),
        RegField.bit("shading", 1, ((0, "toon"), (1, "highlight")), "Polygon shading"),
        RegField.bit("alpha_test", 2, (), "Alpha test"),
        RegField.bit("alpha_blending", 3, (), "Alpha blending"),
        RegField.bit("anti_aliasing", 4, (), "Anti-aliasing"),
        RegField.bit("edge_marking", 5, (), "Edge marking"),
        RegField.bit("fog_alpha_only", 6, (), "Fog color/alpha mode (0=alpha+color, 1=alpha only)"),
        RegField.bit("fog_enable", 7, (), "Fog master enable"),
        RegField.bits("fog_shift", 8, 11, (), "Fog depth shift"),
        RegField.bit("rdlines_underflow", 12, (), "Color buffer RDLINES underflow"),
        RegField.bit("poly_overflow", 13, (), "Polygon/vertex RAM overflow"),
        RegField.bit("rear_plane", 14, ((0, "blank"), (1, "bitmap")), "Rear-plane mode"),
    )
    master_bright = (
        RegField.bits("factor", 0, 4, (), "Brightness factor (0-16)"),
        RegField.bits("mode", 14, 15, ((0, "disable"), (1, "up"), (2, "down"), (3, "reserved")),
                      "Brightness mode"),
    )
    registers = [
        Register("DISPCNT_A", 0x04000000, 4, dispcnt, "LCD control (engine A)"),
        Register("DISPCNT_B", 0x04001000, 4, dispcnt, "LCD control (engine B)"),
        Register("DISP3DCNT", 0x04000060, 4, disp3dcnt, "3D display control"),
        Register("MASTER_BRIGHT_A", 0x0400006C, 2, master_bright, "Master brightness (engine A)"),
        Register("MASTER_BRIGHT_B", 0x0400106C, 2, master_bright, "Master brightness (engine B)"),
    ]
    for i in range(4):
        registers.append(Register(f"BG{i}CNT_A", 0x04000008 + 2 * i, 2, bgcnt, f"BG{i} control (engine A)"))
        registers.append(Register(f"BG{i}CNT_B", 0x04001008 + 2 * i, 2, bgcnt, f"BG{i} control (engine B)"))
    return registers
