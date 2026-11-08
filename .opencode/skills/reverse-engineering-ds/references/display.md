# Display: renderer oracle, tile sheets and text pipeline

Read `concepts.md` first. These techniques cover reading what is on screen and
mapping it back to VRAM/data.

## Technique 2 — The emulator renderer as oracle

**Goal:** see a screen region or a single layer without reimplementing BG/OBJ/3D.

Use `render_layer(engine, layer)` — it drives the emulator's own renderer for one
layer (engine A/B × bg0-3/obj/3d) and writes PNGs. `video_state(engine)` decodes
DISPCNT/BGxCNT/scroll/brightness; `vram_layout()` gives the real bank mapping
(VRAMCNT is write-only on hardware, but the emulator exposes it).

Hand-composing tiles/sprites/palettes is guesswork; the renderer is ground truth.
Only fall back to manual decoding to extract a raw asset for offline tools.

## Technique 6 — Reading VRAM as tile sheets

**Goal:** find a font/atlas or text before composing the full screen.

Dump the relevant VRAM window (`mem_dump_file`, e.g. OBJ `0x06400000`/`0x06600000`,
BG `0x06000000`/`0x06200000`) and view it as a **tile sheet** (4bpp/8bpp, common
strides 8/16/32 tiles per row). Recognizable glyphs confirm the text lives in that
bank, and the neighboring tiles give the atlas. Then use Technique 2 to render the
actual composition.

## Technique 12 — Text/UI rendering pipeline (game-agnostic)

**Goal:** map visible text/boxes to data and code, and avoid patching the wrong
stage.

Common pipeline (names vary; map them per game and record with
`decomp_snippet`):

```
decode resource (LZ/other) -> allocate surface -> measure text
  -> layout/align -> walk glyphs -> draw glyph -> clip -> blit/copy to surface
  -> DMA/upload to VRAM -> BG map cells
```

Practical rules:

- **Surface descriptor**: `dst`, `width`, `height`, `bpp`, buffer size. The
  buffer is `width * height * bytes_per_tile` (4bpp tile = 32 B, 8bpp = 64 B).
  The size is often stored in the element/template; changing `width` **after**
  allocation overflows the buffer and the next heap structure. To widen a box,
  change the resource/element before allocation, or reallocate and update
  descriptor/DMA/map.
- **Text source**: usually an NFTR font plus a UTF-16 string; the same string is
  used for measure and draw. Align flags (right/center) only shift the pen; the
  final clip is the surface/cell limit.
- **Box map**: the map is made of cells; the text run must fit the cells and the
  tile range. A static upload (e.g., a BG layer refreshed every frame) can
  overwrite the last tiles. Check the upload destination and tile range before
  blaming the text engine.
- **Verify RAM vs VRAM byte-for-byte** for the strip, then use `map_cell`
  (`entry_addr`, `screen_base`, `char_base`) and `vram_tile_bytes` to confirm the
  cell/tile. Do not assume a raw `read_vram` address is the cell you think.
- **First glyph missing/clipped**: check the pen offset/alignment and the surface
  clip, not just the string. The glyph may be drawn at a negative x and clipped.
- **DMA length may be derived** from the element size (`w*h*bytes`), not a
  constant; patching it is usually unnecessary.

## Technique 14 — 3D engine inspection (state, polygons, textures, GXFIFO)

**Goal:** debug a 3D scene from data, not from screenshots.

Read the emulator's own 3D core; do not reimplement the geometry pipeline.
`gpu3d_state`, `gpu3d_polygons` and `gpu3d_textures` come from a **one-shot
snapshot at VBlank** (frame complete), so they describe the same frame. If the
emulator is paused the snapshot times out — resume and retry.

- **`gpu3d_state`**: enable flags, DISP3DCNT/GXStat, FIFO levels, matrix mode,
  projection/position/vector/texture matrices, viewport, fog and counts. Confirm
  the transform/viewport before blaming geometry.
- **`gpu3d_polygons(max_items, vertices)`**: polygons of the rendered frame with
  per-vertex **final screen position** (x/y/z/w), color and UV. Use `screenpos`
  to map a visible element to a polygon — the basis for repositioning.
- **`gpu3d_textures` + `gpu3d_texture_dump`**: unique `(TexParam, TexPalette)`
  and PNG decode (reuses the renderer's decoder). Good for atlases/formats.
- **`gxfifo_trace_start/read/stop`**: order and queue depth of GXFIFO entries
  (`name`, `params`, `pc`, `frame`, `fifo`), decoded into readable commands
  (`begin_vtxs`, `mtx_load_4x4`, `texcoord`, `vtx_16`, `end_vtxs`, …). This is
  the **enqueue order** on the writer path, not the executed instruction stream.
  For DMA-fed FIFO, `pc` is the CPU PC at the write; pair with `dma_trace` when
  the DMA programmer matters.
- **Image oracle**: `render_layer(engine=A, layer=3d)` still shows the actual
  composition. Combine image + state + polygons + trace.

Practical rules:

- Screen positions are computed at polygon submission (viewport transform), so
  they live in the polygon dump, not in the `vtx` command.
- The trace shows what the writer pushed; the polygons show the result. Use both.
- Snapshot/polygons/textures are per completed frame; freeze (Technique 1) or
  step to a frame boundary when comparing.
