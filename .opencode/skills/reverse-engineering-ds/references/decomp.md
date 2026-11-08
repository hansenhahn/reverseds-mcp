# Decomp: assets, overlay ownership and patching

Read `concepts.md` first. These techniques cover going from an asset to its file
and code, keeping decomp units honest, and producing a minimal reproducible
patch.

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
  with the candidate list + resident overlay/caller, not the first match.
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

- `overlay_for_address` returns **all** candidates plus `ambiguous`; pass
  `overlay=` (or set the resident one with `overlay_select`) to pick. Never take
  the first candidate when bases are shared.
- `addr_valid(addr, overlay=, code_base=)` resolves the overlay and can report the
  code offset; if you only have the y9 offset, subtract the prefix yourself. Do
  not mix the two systems in the same document.
- `symbol_define(..., overlay=)` plus `symbol_lookup(addr, overlay=)`/
  `symbol_load(path, overlay=)` are overlay-aware; still keep a per-unit `.map`
  and audit it.

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
