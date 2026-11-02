---
name: reverse-engineering-ds
description: Game-agnostic techniques for reverse engineering Nintendo DS games with the re-mcp MCP server and the melonDS fork (control channel + GDB stub). Covers frame-accurate freeze/step, renderer-as-oracle, differential memory analysis, DMA/IO tracing, overlay and address math, watchpoint/hit-log semantics, text/UI pipeline mapping, and decomp/patch standardization. Use for NDS animations, HUDs, graphics, assets, overlays and the code that produces them.
metadata:
  version: "0.2"
---

# Reverse engineering NDS games (re-mcp + melonDS)

A toolbox of techniques for figuring out how an NDS game produces what you see on
screen (animations, HUDs, graphics, assets) and which code drives it. Each
technique states its goal, tools and steps.

The rules here are **game-agnostic**: read the target's tables (y9/y7, headers,
maps) instead of hardcoding addresses. Worked examples at the end are
illustrative only.

## Toolchain & topology

- **melonDS fork** (host) exposes two independent channels:
  - **Control channel** (JSON-RPC over a Unix socket): input, screen capture,
    savestates, deterministic frame-step, layer render, video/VRAM/IO state,
    cart/DMA traces.
  - **GDB stub** (ARM9 `:3333`, ARM7 `:3334`): breakpoints, watchpoints,
    registers, memory, stepping, disassembly.
- **re-mcp** connects to the socket (bind-mount) and the stub (host network).
  Verify with `health_check`.
- **Provenance/confidence tools**: `rom_info` (the running ROM is the source of
  truth), `rom_details` (header/y9/runtime overlay), `addr_valid` (hex/dec,
  alignment, region, overlay), `debug_slots` (hardware watchpoint slots),
  `list_breakpoints`.
- **Two-channel golden rule**: attaching the debugger halts the CPU; without it
  the emulator runs free. `emu_step_frame` bridges them (Technique 1).

## Definitions (game-agnostic)

- **Static code**: the ARM9/ARM7 binary mapped at a fixed RAM address. Its end is
  game-specific; do not hardcode it — read the ROM header/overlay table.
- **Overlay**: a file (and its RAM image) loaded on demand. The y9/y7 table gives
  `ram_address`, `ram_size`, `bss_size`, `file_id`, `sinit_start/end` and
  flags/compression. Several overlays may share the same `ram_address`.
- **Overlay file vs code base**: an overlay file may carry a **prefix/header**
  (sinit/loader/padding) before the loaded code. `ram_address` is the load base;
  `code_base = ram_address + prefix` is where the game code the CPU executes
  starts. Keep two offsets: `file_offset = addr - ram_address` and
  `code_offset = addr - code_base`.
- **Sinit**: y9 `sinit_start/end` describe static-initializer code/data. They are
  not necessarily the file prefix; inspect them instead of conflating the two.
- **RAM / VRAM / OAM / palette**: RAM is the CPU address space; VRAM is mapped per
  engine A/B for BG and OBJ; OAM and palettes have their own windows. A CPU read
  and the engine's view are not automatically the same thing (verify).
- **BG/OBJ model**: a layer has a `char_base` (tiles), `screen_base` (map) and a
  map made of **cells**; each cell selects a **tile** plus palette/flip bits.
  4bpp/8bpp change the tile stride (32/64 bytes).
- **Surface / text source / font**: a text surface descriptor commonly carries
  `dst`, `width`, `height`, `bpp` and a buffer size. The text source (often an
  NFTR font plus a UTF-16 string) is measured, laid out, clipped and blitted into
  the surface; the surface is then uploaded to VRAM.
- **Watchpoint / hit log**: a watchpoint triggers on an access (write/read/access)
  to an address range; the hit log records many hits without stopping. Treat the
  logged `pc`/`addr` as **observations with hardware caveats** (Technique 11).
- **DMA transfer**: `{src, dst, len, cpu, pc, DMAxCNT}`. DMA writes do **not**
  trigger CPU hardware watchpoints.

## Technique 1 — Frame-accurate freeze & inspect

**Goal:** stop on an exact frame and inspect it, even mid-animation.

`emu_step_frame(N)` is the atomic advance **and** the stop. With the debugger
attached the stop is the stub's own halt, so "run N frames and inspect" is a
single call with no latency window. Timing: 1 frame ≈ 1/60 s.

Steps:

0. `savestate_save(slot)` at a known point — this is your undo. Reload it before
   each attempt.
1. `debug_connect("arm9")` — CPU halts.
2. Arm input while halted: `input_touch(x, y)` / `input_key(mask)` set state even
   when stopped.
3. `emu_step_frame(N)` — input is processed across the N frames, then it stops.
4. `input_release`.
5. Inspect: `screen_capture`, `video_state`, `vram_layout`, `render_layer`,
   `mem_dump_file`, `debug_read_register`, `disassemble`.
6. Loop: `savestate_load(slot)` → re-arm input → `emu_step_frame(N)`. Resume with
   `debug_resume` or another `emu_step_frame`.

Bisect the frame count in blocks (e.g., 60) and capture between blocks when you
don't know the target frame. **Never run free and hope.**

## Technique 2 — The emulator renderer as oracle

**Goal:** see a screen region or a single layer without reimplementing BG/OBJ/3D.

Use `render_layer(engine, layer)` — it drives the emulator's own renderer for one
layer (engine A/B × bg0-3/obj/3d) and writes PNGs. `video_state(engine)` decodes
DISPCNT/BGxCNT/scroll/brightness; `vram_layout()` gives the real bank mapping
(VRAMCNT is write-only on hardware, but the emulator exposes it).

Hand-composing tiles/sprites/palettes is guesswork; the renderer is ground truth.
Only fall back to manual decoding to extract a raw asset for offline tools.

## Technique 3 — Differential analysis

**Goal:** locate buffers/regions that change between two states (e.g.,
before/after a transition).

Use `mem_snapshot(name, addr, size)` on a **small** region and `state_diff(name)`
after the change. Diffs of large RAM (4 MB) are useless — scope to VRAM, OAM,
palettes, or a few KB around a suspected buffer. Combine with Technique 1 to diff
consecutive frames.

## Technique 4 — DMA / IO tracing

**Goal:** find the code that fills VRAM/registers when a CPU watchpoint misses it.

VRAM is usually filled by **DMA**, which does not trigger CPU hardware
watchpoints. Use `dma_trace_start` / `dma_trace_read` / `dma_trace_stop`: each
transfer is decoded (src/dst, length, decoded `DMAxCNT` fields) together with the
**PC that programmed the channel** — the missing link from "this data is in VRAM"
to "this code put it there". Prefer filtering/aggregation (Technique 11) over
dumping every transfer. `io_read` decodes memory-mapped registers; watchpoints on
IO addresses and `find_writer`/`find_reader` complement this.

DMA can be **deferred** (FIFO/flush at end of frame). If the trace shows the
upload after the draw call, that is normal; do not mistake the deferred upload for
the cause of a layout bug.

## Technique 5 — Asset-identification pipeline

**Goal:** go from a visible asset to the file bytes and the code that loads/draws
it.

1. `cart_trace_start` while the asset loads; `cart_trace_read`/`cart_read_files`
   to see which files are read (verify the mounted ROM matches the running game).
2. `mem_snapshot` + `state_diff` around the load to find the RAM buffer.
3. `dma_trace_*` to see the buffer being uploaded (e.g., to VRAM).
4. `set_watchpoint` (with a `condition`) / `find_writer` on the asset struct or
   the register that triggers the upload; `disassemble(pc)`.
5. Extract with `cart_file`/`cart_read` + `mem_dump_file`, then rebuild the asset
   offline.

## Technique 6 — Reading VRAM as tile sheets

**Goal:** find a font/atlas or text before composing the full screen.

Dump the relevant VRAM window (`mem_dump_file`, e.g. OBJ `0x06400000`/`0x06600000`,
BG `0x06000000`/`0x06200000`) and view it as a **tile sheet** (4bpp/8bpp, common
strides 8/16/32 tiles per row). Recognizable glyphs confirm the text lives in that
bank, and the neighboring tiles give the atlas. Then use Technique 2 to render the
actual composition.

## Technique 7 — Confidence: address first, prove the write

**Goal:** eliminate silent errors before chasing causality.

1. `rom_info` — confirm which ROM is actually loaded (the emulator is the source of
   truth; never trust a path from the host). Use `rom_details` for y9/runtime
   overlay.
2. `addr_valid(value)` — normalize hex/dec, check alignment, region and overlay
   **before** any `mem_write`/`set_breakpoint`. Unmapped is a valid result.
3. `debug_slots()` + `list_breakpoints` — see hardware slot usage, whether a
   watchpoint fell back to software, and every write/read/access watchpoint before
   blaming the stub. Read watchpoints work; access watchpoints may be refused.
4. **Prove the write** with a watchpoint (`find_writer`/`set_watchpoint`); a NOP +
   screenshot is not proof (residual tiles/atlases lie).
5. Re-check `addr_valid`/`rom_info` after an overlay reload or savestate change.

## Technique 8 — Conditional breakpoints and backtrace

**Goal:** stop only on the event you care about and reconstruct the call chain.

- `set_breakpoint(addr, condition="$r3 == 0x30")` — gdb evaluates the condition;
  you only stop when it is true (register or memory).
- `set_breakpoint(addr, commands=[...])` — commands run on the hit. Auto-patch
  pattern: `["silent", "set {unsigned int}0x... = 0x...", "continue"]` (write the
  immediate and keep running, no `resume → wait → mem_write` loop).
- `debug_backtrace()` — gdb frames first (`source="gdb"`); when gdb returns fewer
  than four, the MCP scans the stack (`sp..sp+0x800`) and appends even-aligned
  return addresses in ITCM/main RAM/BIOS as `source="stack"`. Candidates are
  confirmed by a preceding `bl`/`blx`; treat stack frames as heuristic and confirm
  the call site before trusting them.

## Technique 9 — Cold reset, hit log and DMA/VRAM watchpoints

**Goal:** reproduce a boot deterministically and observe events without stopping
on each one.

- `emu_reset()` — cold reset. BPs/WPs survive; with gdb attached the CPU stays
  halted at a deterministic boot entry (read the reset vector/PC; the exact
  address is game-specific). Without gdb the game runs again.
- `hit_log_start(core, capacity)` / `hit_log_read(core)` — records breakpoint and
  watchpoint hits **without stopping**; `kind` is `breakpoint`, `write`, `read`,
  `access` or `dma-write`; `dropped` counts ring overflows. Use
  `hit_log_clear`/`hit_log_stop` at the end, and read Technique 11 before
  interpreting the PC/address.
- **DMA/VRAM**: arm `set_watchpoint(vram_addr, "write")` and enable the hit log;
  when a DMA fills the range, the log shows `dma-write` with the PC that
  programmed the DMA. Without the log, the stop also lands on that PC.

## Technique 10 — Overlay model and decomp unit ownership

**Goal:** keep static and overlay code in the right unit, avoid duplicate/partial
decompilations, and make addresses and offsets unambiguous.

### 10.1 Read the overlay/address model

Build the unit map once per ROM with `overlay_list`/`rom_details` (y9/y7
`ram_address`, `ram_size`, `bss_size`, `sinit_start/end`, `file_id`). Never
hardcode a game's bases into reusable rules.

- **Static ARM9** ends at the first overlay's load base (or at the ARM9 image
  end); `addr_valid` is the authority, not a raw threshold.
- **Overlay file vs code base**: if the file has a prefix/header (sinit/loader),
  `code_base = ram_address + prefix`. Compute both `file_offset` and
  `code_offset`; use `code_offset` for decomp `.org`/unit offsets and
  `file_offset` for file edits.
- **Shared bases**: several overlays can share `ram_address`. The same absolute
  address can belong to different overlays depending on what is resident. Resolve
  with the candidate list + resident overlay/caller, not the first match. Use
  `overlay_for_address` (candidates + `ambiguous`), `overlay_details` (y9/FAT/
  compression) and `overlay_select` (declare the resident overlay; session state,
  not proof). Revalidate the selection after an overlay reload.
- **Sinit**: y9 `sinit_start/end` are static-initializer pointers; they are not
  necessarily the file prefix. Do not conflate them.
- **Prefix region**: addresses below `code_base` but inside `[ram_address,
  ram_address + ram_size)` belong to the overlay (loader/sinit/code), not to the
  static ARM9 binary. A threshold like "below code_base = static" misclassifies
  that region.

### 10.2 Ownership rules

1. **One canonical body per address.** If the same function has 4bpp/8bpp
   branches, keep both in the owning unit; do not fork a "screen variant" into an
   overlay file.
2. Overlay files only declare/call shared functions (prototypes from the static
   `.h`).
3. **Audit before committing:** extract every `/* 0xADDR ... */` from the decomp
   files, call `addr_valid` for each, and flag any address whose region/overlay
   does not match the file's unit. Also flag the same address defined twice.
4. Re-run the audit after an overlay reload or when adding an overlay.
5. **Syntax check (hygiene):** `gcc -fsyntax-only` on each unit. Zero errors is
   the bar. Warnings are TODOs (32-bit host pointer casts, `const`), not
   blockers. Never leave `...` placeholders or undeclared identifiers "for
   later"; that is what makes a decomp uncompilable forever.
6. **Document the base math** in the unit header: y9 base, prefix, code base, and
   which offset the `.map`/comments use.

### 10.3 Tool caveats

- `overlay_for_address` returns **all** candidates with `ambiguous`; when the
  base is shared, do not pick the first. The selected `overlay` is explicit
  (`overlay=`), the active `overlay_select`, or the only candidate; otherwise it
  is `null`.
- `overlay_details` reports `file_offset`/`file_size` (FAT), `compressed`/
  `compressed_size` and optional `code_base`/`prefix_size`. `addr_valid` reports
  `offset_file` (always) and `offset_code` (when the code base is known); do not
  mix the two systems in the same document.
- `symbol_define(..., overlay=)` stores `overlay` as metadata; `symbol_lookup`
  resolves by address without filtering overlay. Keep a per-unit `.map` and audit
  it; prefer an explicit resident-overlay check when bases are shared.

### 10.4 Decomp style and standardization

- **One unit = one `.c` + one `.h` + one `.map`.** Edit the unit's `.c`; do not
  create one `.c` per function.
- **Unit header:** file name, what it is, "not compilable" warning, static vs
  overlay, and the base math (y9/prefix/code). Use a banner per function:
  `/* 0xADDR — name */`.
- **Types in the `.h`**: typedefs/structs/prototypes. The `.c` includes the `.h`
  and contains only bodies.
- **Identifiers in English**: types, functions, fields, globals, macros.
  Comments/prose may stay in the project language.
- **Known fields by meaning**, not offset (`width_in_tiles`, `tile_base`,
  `bytes_per_tile`, `map_start_x`); unknown fields stay `field_XX`.
- **Raw-layout mirror structs** must use the same field names and offsets as the
  template, so casts/`memcpy` stay honest.
- **Runtime-only symbols are stubs**: `static T *g_x = NULL;` or a known address
  in a comment; never leave an undeclared identifier.
- **ASM + C**: keep a summarized ASM in comments and the full ASM in
  `decomp.json`; annotate key instruction addresses in the C. Mark partial models
  explicitly and keep a "not yet decompiled" section.
- **Contract first**: args (`r0..r3`/stack), return, reads/writes, calls, and
  uncertainty markers. Validate at runtime with `args_on_hit`/`contract_check`.
- **Original data vs patch**: the unit documents the original; the patch lives in
  a separate `.asm`.
- **Coverage table**: being in the `.map` does not mean decompiled; track status.
- **Version control**: commit the decomp docs, `.map` and `.asm`; untracked docs
  are lost docs.

## Technique 11 — Watchpoint and hit-log semantics

**Goal:** interpret runtime hits without inventing causality.

- **PC may be ahead of the access.** On ARM the logged PC can be `pc+4`; on Thumb,
  `pc+2`. Disassemble around the PC and look for the actual `ldr/str/ldm/stm`. If
  the tool exposes a faulting PC, prefer it; otherwise treat `pc-4`/`pc-2` as
  candidates.
- **Granularity is a word.** A watchpoint triggers on the aligned word that
  contains the access. The byte-level `addr` in a log is not proof of the exact
  byte; adjacent UTF-16 chars cannot be distinguished with one watchpoint.
- **RMW triggers read watchpoints.** `swpb` (and other read-modify-write
  sequences) can make a read watchpoint fire on the decoder/writer, not on the
  consumer. For decompressed data, arm the watchpoint **after** decompression, or
  filter by PC, or use the hit log to list all writers and take the last one
  before the DMA.
- **DMA is invisible to CPU watchpoints.** Use DMA/VRAM watchpoints or the DMA
  trace (Technique 4).
- **Hit log for mass, stop for context.** Use `hit_log_*` to count/filter; stop
  for registers/stack/backtrace. Confirm with a second witness (disassemble,
  register value, memory diff).
- **Read the access, not just the address.** If a read watchpoint hits the LZ
  decoder, you found the producer of the buffer; the consumer is later. Arm after
  the producer or filter by PC.

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

## Technique 13 — Patch and rebuild standardization

**Goal:** make a minimal, reproducible patch and prove it outside the savestate.

1. **Separate original from patch.** The decomp documents the original
   values/bytes; the patch is a separate `.asm` with `.org` in code/RAM addresses.
2. **Check the offset math.** Confirm whether the field is at `file_offset` or
   `code_offset`; account for the prefix. Dump the template/struct and verify the
   field before writing.
3. **Minimal patch.** Prefer one instruction or a few data words. For a data
   template, patch the template, not every draw call.
4. **Rebuild the unit.** Overlay decompress → `armips` → recompress → repack the
   `.nds`. Verify the expected words changed and nothing else.
5. **Test outside the savestate.** Reload the patched ROM from boot; a savestate
   can mask a stale overlay or cache.
6. **Watch static uploads.** A layer refreshed every frame can overwrite patched
   tiles; move the tile base or reserve space.
7. **Keep a patch table**: field, offset (file/code), original, new, and why.
8. **Do not patch derived sizes** (DMA length, buffer size) unless the allocation
   was also changed.

## Canonical flow (7 phases)

1. **Inventory/provenance** — `rom_info`, `rom_details`, `overlay_list`; record
   y9 base, prefix and code base; `addr_valid` for the addresses you will touch.
2. **Locate the displayed layer** — `video_state`, `vram_layout`, `render_layer`.
3. **Display → data** — `map_cell` (`entry_addr`/`screen_base`/`char_base`),
   tile bytes, RAM source (`mem_dump_file`, `state_diff`), RAM↔VRAM compare.
4. **Find the writer** — conditional BP + hit log (Technique 11); DMA/VRAM WP for
   uploads; `debug_slots` before arming.
5. **Model in C** — `addr_valid(func)` for the owning unit; contract first
   (args/offsets/effects); validate with `args_on_hit`/`contract_check`.
6. **Prove with a minimal patch** — one instruction/data word, capture, compare;
   control staleness.
7. **Package** — overlay decompress → `armips` → recompress → repack; verify only
   the expected words changed.

## Anti-patterns

- Patching composition/measure/bbox and expecting the display to change.
- Concluding from a NOP screenshot without checking staleness.
- Editing VRAM and assuming the RAM map *is* the display (or vice versa).
- Mixing builds (ROM × savestate × overlay) or trusting a host ROM path.
- Using the gdb CLI while the MCP holds the stub.
- Writing an address without `addr_valid` ("it looked right in hex").
- Trusting the first overlay match when bases are shared.
- Confusing `file_offset` with `code_offset`, or ignoring the file prefix/sinit.
- Treating the hit-log `pc`/`addr` as the exact faulting instruction/byte.
- Treating a read-watchpoint hit as a consumer without checking RMW/`swpb`.
- Classifying a function by the overlay that **calls** it instead of by its own
  address/ram base.
- Decompiling the same address twice (4bpp in the static unit, 8bpp in an
  overlay) instead of one body with both branches.
- Widening a text box after allocation (buffer overflow) or forgetting the static
  upload that overwrites trailing tiles.
- Hardcoding a game's bases/addresses into reusable rules or docs.

## Golden rules

- **Savestate is undo**: save at the target point; reload before destructive steps.
- **Debugger attached = CPU halted**: input and frames only advance via
  `emu_step_frame` / `debug_resume`.
- **Load state before connecting gdb** (savestate_load with a halted target can
  time out).
- **Bulk memory goes to a file** (`mem_dump_file`); copying hex by hand is
  error-prone.
- **Name the screen (top/bottom) and engine (A/B)** in every capture and dump.
- **Reuse the toolkit**: prefer existing parsers/extractors over reimplementing
  formats.
- **y9/y7 is the source of truth** for overlay bases; read it, don't hardcode.
- **Separate file offset, code offset and RAM address** in every document.
- **One canonical body per address**; branches stay with the owning unit.
- **Validate with two witnesses** (e.g., disassembly + register, RAM + VRAM,
  map + render) before concluding.
- **Keep original data and patch separate**, and repack/test outside the savestate.

## Worked examples (illustrative only)

### KH 358/2 Days — shared overlay base and load screen

- Overlays 22 and 25 share `ram_address 0x02082960`; `overlay_for_address` may
  return 22 for an address that belongs to 25 depending on what is resident.
  Always confirm the resident overlay/caller.
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
- This example is illustrative; the reusable rules are in Technique 10.

### Hotel Dusk — intro text animation

Touch point on the bottom (touch) screen: `(125, 100)`.

```
savestate_load(0)         # title screen (PRESS START)
debug_connect("arm9")     # CPU halts
input_touch(125, 100)     # arm START touch
emu_step_frame(60)        # ~1 s; repeat 60 at a time
#  the text appears only around ~300 frames (~5 s) after the touch
screen_capture("both")    # freeze and show the text animation
```

Observed (~frame 300): top `FRIDAY DECEMBER 1972…`, bottom `NEW YORK 5:07 P…`
(rotated 90°, book mode). That frame is now reproducible from the savestate for
VRAM dumps and disassembly.
