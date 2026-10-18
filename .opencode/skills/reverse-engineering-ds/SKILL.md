---
name: reverse-engineering-ds
description: Techniques for reverse engineering Nintendo DS games with the re-mcp MCP server and the melonDS fork (control channel + GDB stub). Covers frame-accurate freeze/step, using the emulator renderer as an oracle, differential memory analysis, DMA/IO tracing, the asset-identification pipeline, and reading VRAM as tile sheets. Use when analyzing NDS animations, HUDs, graphics, assets, or the code that produces them through the emulator.
metadata:
  version: "0.1"
---

# Reverse engineering NDS games (re-mcp + melonDS)

A toolbox of techniques for figuring out how an NDS game produces what you see on screen
(animations, HUDs, graphics, assets) and which code drives it. Each technique states its
goal, the tools, and the steps.

## Toolchain & topology

- **melonDS fork** (host) exposes two independent channels:
  - **Control channel** (JSON-RPC over a Unix socket): input, screen capture, savestates,
    deterministic frame-step, layer render, video/VRAM/IO state, cart/DMA traces.
  - **GDB stub** (ARM9 `:3333`, ARM7 `:3334`): breakpoints, watchpoints, registers, memory,
    stepping, disassembly.
- **re-mcp** connects to the socket (bind-mount) and the stub (host network). Verify with
  `health_check`.
- **The two-channel golden rule**: attaching the debugger halts the CPU; without it, the
  emulator runs free. `emu_step_frame` bridges them (see Technique 1).

## Technique 1 — Frame-accurate freeze & inspect

**Goal:** stop on an exact frame and inspect it, even mid-animation.

`emu_step_frame(N)` is the atomic advance **and** the stop. With the debugger attached the
stop is the stub's own halt (the same "stopped" the debugger sees), so "run N frames and
inspect" is a single call with no latency window. Timing: 1 frame ≈ 1/60 s (~0.018 s), so N
frames ≈ N/60 s.

Steps:

0. `savestate_save(slot)` at a known point — this is your undo. Reload it before each attempt.
1. `debug_connect("arm9")` — CPU halts.
2. Arm input while halted: `input_touch(x, y)` / `input_key(mask)` set state even when stopped.
3. `emu_step_frame(N)` — input is processed across the N frames, then it stops again.
4. `input_release`.
5. Inspect: `screen_capture` (reflects the frozen frame), `video_state`, `vram_layout`,
   `render_layer`, `mem_dump_file`, `debug_read_register`, `disassemble`.
6. Loop: `savestate_load(slot)` → re-arm input → `emu_step_frame(N)`. Resume with
   `debug_resume` or another `emu_step_frame`.

Bisect the frame count in blocks (e.g., 60) and capture between blocks when you don't know
the target frame. **Never run free and hope.**

## Technique 2 — The emulator renderer as oracle

**Goal:** see a screen region or a single layer without reimplementing BG/OBJ/3D.

Use `render_layer(engine, layer)` — it drives the emulator's own renderer for one layer
(engine A/B × bg0-3/obj/3d) and writes PNGs. `video_state(engine)` decodes DISPCNT/BGxCNT/
scroll/brightness; `vram_layout()` gives the real bank mapping (VRAMCNT is write-only on
hardware, but the emulator exposes it).

Hand-composing tiles/sprites/palettes is guesswork; the renderer is ground truth. Only fall
back to manual decoding to extract a raw asset for offline tools.

## Technique 3 — Differential analysis

**Goal:** locate buffers/regions that change between two states (e.g., before/after a
transition).

Use `mem_snapshot(name, addr, size)` on a **small** region and `state_diff(name)` after the
change. Diffs of large RAM (4 MB) are useless — scope to VRAM, OAM, palettes, or a few KB
around a suspected buffer. Combine with Technique 1 to diff consecutive frames.

## Technique 4 — DMA / IO tracing

**Goal:** find the code that fills VRAM/registers when a CPU watchpoint misses it.

VRAM is usually filled by **DMA**, which does not trigger CPU hardware watchpoints. Use
`dma_trace_start` / `dma_trace_read` / `dma_trace_stop`: each transfer is decoded (src/dst,
length, decoded `DMAxCNT` fields) together with the **PC that programmed the channel** — the
missing link from "this data is in VRAM" to "this code put it there". `io_read` decodes
memory-mapped registers; watchpoints on IO addresses (`0x040000B0+`) and `find_writer`/
`find_reader` complement this.

## Technique 5 — Asset-identification pipeline

**Goal:** go from a visible asset to the file bytes and the code that loads/draws it.

1. `cart_trace_start` while the asset loads; `cart_trace_read`/`cart_read_files` to see which
   files are read (verify the ROM mounted in the container matches the running game).
2. `mem_snapshot` + `state_diff` around the load to find the RAM buffer.
3. `dma_trace_*` to see the buffer being uploaded (e.g., to VRAM).
4. `set_watchpoint` (with a `condition`) / `find_writer` on the asset struct or the register
   that triggers the upload to catch the code; `disassemble(pc)`.
5. Extract with `cart_file`/`cart_read` + `mem_dump_file`, then rebuild the asset offline.

## Technique 6 — Reading VRAM as tile sheets

**Goal:** find a font/atlas or text before composing the full screen.

Dump the relevant VRAM window (`mem_dump_file`, e.g. OBJ `0x06400000`/`0x06600000`, BG
`0x06000000`/`0x06200000`) and view it as a **tile sheet** (4bpp/8bpp, common strides 8/16/32
tiles per row). Recognizable glyphs ("DECEMB", "19") confirm the text lives in that bank, and
the neighboring tiles give the atlas. Then use Technique 2 to render the actual composition.

## Golden rules

- **Savestate is undo**: save at the target point; reload before destructive steps.
- **Debugger attached = CPU halted**: input and frames only advance via `emu_step_frame` /
  `debug_resume`.
- **Load state before connecting gdb** (savestate_load with a halted target can time out).
- **Bulk memory goes to a file** (`mem_dump_file`); copying hex by hand is error-prone.
- **Name the screen (top/bottom) and engine (A/B)** in every capture and dump.
- **Reuse the toolkit**: prefer existing parsers/extractors over reimplementing formats.

## Worked example — Hotel Dusk intro text animation

Touch point on the bottom (touch) screen: `(125, 100)`.

```
savestate_load(0)         # title screen (PRESS START)
debug_connect("arm9")     # CPU halts
input_touch(125, 100)     # arm START touch
emu_step_frame(60)        # ~1 s; repeat 60 at a time
#  the text appears only around ~300 frames (~5 s) after the touch
screen_capture("both")    # freeze and show the text animation
```

Observed (~frame 300): top `FRIDAY DECEMBER 1972…`, bottom `NEW YORK 5:07 P…` (rotated 90°,
book mode). That frame is now reproducible from the savestate for VRAM dumps and disassembly.
