# Runtime debugging: freeze, observe, prove causality

Read `concepts.md` first. These techniques cover stopping at a deterministic
point, finding who wrote what, and interpreting hardware/software observation
caveats.

## Technique 1 — Frame-accurate freeze & inspect

**Goal:** stop on an exact frame and inspect it, even mid-animation.

`emu_step_frame(N)` is the atomic advance **and** the stop. With the debugger
attached the stop is the stub's own halt, so "run N frames and inspect" is a
single call with no latency window. Timing: 1 frame ≈ 1/60 s.

Steps:

0. `savestate_save(slot)` (or `savestate_save(name=...)`) at a known point — this
   is your undo. It writes a verified sidecar (CRC/frame/gamecode); reload it before
   each attempt.
1. `debug_connect("arm9")` — CPU halts.
2. Arm input while halted: `input_touch(x, y)` / `input_key(mask)` set state even
   when stopped.
3. `emu_step_frame(N, snapshot=True)` — input is processed across the N frames,
   the 3D snapshot is captured on the last frame, and it stops.
4. `input_release`.
5. Inspect: `screen_capture`, `video_state`, `vram_layout`, `render_layer`,
   `gpu3d_*` with `source="last"`, `mem_dump_file`, `debug_read_register`,
   `disassemble`.
6. Loop: `savestate_load(slot)` → re-arm input → `emu_step_frame(N, snapshot=True)`.
   Resume with `debug_resume` or another `emu_step_frame`.

Bisect the frame count in blocks (e.g., 60) and capture between blocks when you
don't know the target frame. **Never run free and hope.**

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

### CPU writes that never become DMA

A loader or LZ decompressor can write the destination buffer with ordinary CPU
stores (no DMA). When the DMA trace is empty but the buffer changes, use the CPU
write trace:

- `ram_write_trace_start(addr_start, addr_end)` → resume the scene →
  `ram_write_trace_read(seconds, summary=True)` → `ram_write_trace_stop()`; or
  `watch_range(addr_start, addr_end, seconds)` while the game runs.
- Each write carries `{cpu, addr, value, width, pc}`. `summary` groups by
  `(addr, width, pc)`: a hot store loop in the decompressor/loader shows up as a
  large `count` for one PC.
- Take that PC and `set_breakpoint(pc, kind="hw")` (hardware is the default) to stop
  on the loop; then inspect the source/destination pointers in registers.
- The trace is opt-in (one atomic load per CPU write when off) and covers
  interpreter writes (GDB-enabled build). JIT fastmem writes are not traced; DMA is
  still `dma_trace_*`.

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
  you only stop when it is true (register or memory). Conditions use gdb syntax:
  `$r0`/`$pc`/`$sp` (with `$`), `*(unsigned short*)0x...`.
- `set_breakpoint` defaults to a **hardware** breakpoint (`hbreak`/`Z1`,
  `kind="hw"`). This stub inserts software breakpoints by writing a BKPT into
  memory, and that path is unreliable (reports `hardware: false`, CPU keeps running).
  Use `kind="sw"` only when you have a stub where software BPs are known-good.
- `set_breakpoint(addr, commands=[...])` — commands run on the hit. Auto-patch
  pattern: `["silent", "set {unsigned int}0x... = 0x...", "continue"]` (write the
  immediate and keep running, no `resume → wait → mem_write` loop).
- **A command list ending in `continue` auto-resumes after each hit.** While the
  target runs, `mem_read`/`mem_dump_file` and watchpoint edits fail with
  `alvo em execução` or `leitura incompleta ... veio 0` (the dump needs a halted
  target). Use `debug_resume` + `debug_wait`, or drop `continue` while you need to
  inspect; confirm `emu_status.halted` before reading. This is debugger state, not
  a broken memory bridge.
- **`Invalid hex digit N`/`Broken pipe`/`No registers` are stub desync symptoms**,
  not a condition-parser failure: gdb read a stop reply `Sxx` where it expected
  hex data. Restart the emulator (or at least reconnect) and prefer `kind="hw"`;
  do not rewrite the condition.
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
- **Software breakpoints and RAM writes can wedge this stub.** The BKPT write
  goes through the same `X`/`M` path as `mem_write`; if the session dies or a new
  `debug_connect` says `No registers`, restart the emulator. `set_breakpoint`'s
  hardware default avoids the BKPT write; `cart_override_*` avoids RAM writes for
  asset tests entirely.
