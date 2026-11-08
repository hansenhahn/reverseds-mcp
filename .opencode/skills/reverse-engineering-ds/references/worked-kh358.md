# Worked example: KH 358/2 Days — shared overlay base and load screen

**Illustrative only.** The reusable rules live in `decomp.md` (Technique 10) and
`display.md` (Technique 12). Never hardcode these addresses into generic rules.

- Overlays 22 and 25 share `ram_address 0x02082960`; `overlay_for_address`
  returns **both** candidates (`ambiguous`). Select the resident one with
  `overlay_select`/`overlay=` and confirm the caller.
- `overlay_0000` has y9 `ram_address 0x0204CAC0`, a `0x600` file prefix, and code
  base `0x0204D0C0`. Absolute address = `0x0204CAC0 + file_offset`; code offset =
  `addr - 0x0204D0C0`. Example: `0x0205A734` = code offset `0xD674` = file offset
  `0xDC74`.
- The static ARM9 is below the first overlay; the `[0x0204CAC0, 0x0204D0C0)` block
  belongs to overlay 0 (prefix), not to the static binary.
- Text pipeline observed: `prepare_text → calculate_size/measure_width →
  prepare_line → walk_line → draw_glyph → clip_area → copy_square`; the header
  strip is uploaded by DMA (`0x021F2E00 → 0x06204C20`) and a static BG3 upload
  (`0x062050A0`) can overwrite the last tiles.
