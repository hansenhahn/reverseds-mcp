---
name: reverse-engineering-ds
description: Game-agnostic techniques for reverse engineering Nintendo DS games with the re-mcp MCP server and the melonDS fork (control channel + GDB stub). Covers frame-accurate freeze/step, renderer-as-oracle, 3D state/polygons/textures and GXFIFO tracing, differential memory analysis, DMA/IO tracing, overlay and address math, watchpoint/hit-log semantics, text/UI pipeline mapping, and decomp/patch standardization. Use for NDS animations, HUDs, graphics, assets, 3D scenes, overlays and the code that produces them.
metadata:
  version: "0.7"
---

# Reverse engineering NDS games (re-mcp + melonDS)

A toolbox for figuring out how an NDS game produces what you see on screen
(animations, HUDs, graphics, assets) and which code drives it. The rules are
**game-agnostic**: read the target's tables (y9/y7, headers, maps) instead of
hardcoding addresses.

This file is a **router**. Load `references/concepts.md` first, then open only the
reference for the task at hand.

## How to use

1. `references/concepts.md` — toolchain, topology and shared vocabulary (read once).
2. Pick a task below and open its reference.
3. Worked examples are illustrative only; never copy their addresses into rules.

## Find your task

| You need to... | Reference |
|---|---|
| Stop on an exact frame and inspect/step deterministically | `runtime-debugging.md` T1 |
| Diff regions between two states/frames | `runtime-debugging.md` T3 |
| Find the code that fills VRAM when a CPU watchpoint misses it | `runtime-debugging.md` T4 |
| Validate address/overlay and prove the write | `runtime-debugging.md` T7 |
| Stop on a condition and reconstruct the call chain | `runtime-debugging.md` T8 |
| Cold-reset and record hits without stopping | `runtime-debugging.md` T9 |
| Interpret watchpoint/hit-log PC, granularity and RMW caveats | `runtime-debugging.md` T11 |
| See a layer/region without reimplementing the renderer | `display.md` T2 |
| Find a font/atlas in VRAM as a tile sheet | `display.md` T6 |
| Map text/UI from screen to data and code | `display.md` T12 |
| Inspect a 3D scene: state, polygons, textures, GXFIFO trace | `display.md` T14 |
| Locate a 3D element on screen (for repositioning) | `display.md` T14 |
| Find the RAM source of a 3D texture / display list | `display.md` T14 |
| Go from a visible asset to its files and loader/drawer | `decomp.md` T5 |
| Keep static/overlay decomp units and offsets honest | `decomp.md` T10 |
| Make and verify a minimal reproducible patch | `decomp.md` T13 |
| Run the end-to-end workflow | `decomp.md` canonical flow |
| Close a function honestly (no stub on the critical path) | `decomp-discipline.md` |
| Decide if a stub is acceptable / track debt | `decomp-discipline.md` |
| Avoid scene/context drift while decompiling | `decomp-discipline.md` |
| See a concrete KH 358/2 Days case | `references/worked-kh358.md` |
| See a concrete Hotel Dusk case | `references/worked-hotel-dusk.md` |

## Reference index

- **`references/concepts.md`** — channels, provenance tools, definitions (static
  vs overlay, file/code offsets, VRAM/OAM/palette, cells, surfaces, DMA).
- **`references/runtime-debugging.md`** — Techniques 1, 3, 4, 7, 8, 9, 11: freeze,
  differential analysis, DMA/IO tracing, confidence, conditional BPs/backtrace,
  cold reset/hit log, watchpoint semantics.
- **`references/display.md`** — Techniques 2, 6, 12, 14: renderer as oracle, VRAM
  tile sheets, text/UI pipeline, 3D state/polygons/textures + GXFIFO trace.
- **`references/decomp.md`** — Techniques 5, 10, 13 plus the canonical flow:
  asset identification, overlay ownership/decomp style, patch/rebuild.
- **`references/decomp-discipline.md`** — Definition of Done, stub policy, context
  ledger, controlled vocabulary, runtime-first for order/effect, checkpoints.
- **`references/worked-kh358.md`**, **`references/worked-hotel-dusk.md`** — worked
  examples (illustrative, game-specific).

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
- **No stub on the critical path**: a stub is out-of-scope only; on the path you
  are closing it is a blocker, not "partial".
- **Runtime first for order/effect**; static code explains *why*, it does not
  prove *when*.
- **Keep a context ledger**: label code/resource only after checking the init's
  caller and the active scene.
- **Keep original data and patch separate**, and repack/test outside the savestate.

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
- Treating a stub as the destination or "it compiles" as done (definition of
  done is stricter).
- Presenting a partial model as closed, or "authoritative" before mechanism,
  source and order are all proven.
- Settling execution order/"who wins" purely from static code instead of runtime.
