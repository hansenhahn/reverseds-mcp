# Concepts: toolchain, topology and model

Read this first. It is the shared vocabulary for every other reference.

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

## Tool inventory (current)

Canonical map of the registered tools, grouped by use. This is a **name index**,
not signatures: read the tool's own docstring/returns before calling. If a tool
you need is missing here, it is not registered — do not assume it exists
(`decomp_status`, `project_note`, `write_trace`, `parse_trace` are proposals, not
tools yet).

- **Provenance/ROM**: `rom_info`, `rom_details`, `addr_valid`, `health_check`,
  `ping`, `control_reset`.
- **Overlays/symbols**: `overlay_list`, `overlay_details`, `overlay_for_address`,
  `overlay_select`, `symbol_define`, `symbol_list`, `symbol_load`,
  `symbol_lookup`.
- **Debug/CPU**: `debug_connect`, `debug_disconnect`, `debug_read_register`,
  `debug_write_register`, `debug_step`, `debug_continue`, `debug_resume`,
  `debug_wait`, `debug_interrupt`, `debug_backtrace`, `debug_slots`,
  `list_breakpoints`, `set_breakpoint`, `remove_breakpoint`, `set_watchpoint`,
  `mem_read`, `mem_write`, `mem_dump_file`, `disassemble`, `find_reader`,
  `find_writer`.
- **Hit log / DMA**: `hit_log_start`, `hit_log_stop`, `hit_log_clear`,
  `hit_log_read`, `dma_trace_start`, `dma_trace_read`, `dma_trace_stop`,
  `dma_source`.
- **Display/video**: `video_state`, `vram_layout`, `read_vram`, `vram_tile_bytes`,
  `map_cell`, `cell_at_screen`, `dump_tilemap`, `render_bg_map`, `render_layer`,
  `find_tile_in_ram`, `io_read`, `screen_capture`.
- **3D engine**: `gpu3d_state`, `gpu3d_polygons`, `gpu3d_textures`,
  `gpu3d_texture_dump`, `gxfifo_trace_start`, `gxfifo_trace_read`,
  `gxfifo_trace_stop`. State/polygons/textures come from a VBlank snapshot;
  `render_layer(engine=A, layer=3d)` remains the image oracle.
- **3D asset origin**: `gpu3d_texture_source`, `gxfifo_source`, `origin_start`,
  `origin_stop`, `origin_query`, `find_bytes_in_ram`. Locates the RAM source of a
  texture (content search) and the GXFIFO display list; extraction/import stays
  external.
- **Memory diff**: `mem_snapshot`, `state_diff`.
- **Cartridge/NitroFS**: `cart_list`, `cart_read`, `cart_read_files`, `cart_file`,
  `cart_trace_start`, `cart_trace_read`, `cart_trace_stop`.
- **Input / frame / state**: `input_key`, `input_touch`, `input_touch_tap`,
  `input_tap`, `input_sequence`, `input_merge`, `input_release`, `emu_step_frame`,
  `emu_reset`, `savestate_save`, `savestate_load`.
- **RAM patches**: `patch_set`, `patch_apply`, `patch_clear`, `patch_list`.
- **Decomp helpers**: `args_on_hit`, `contract_check`, `field_xref`,
  `field_writers`, `struct_candidate`, `decomp_snippet`, `diff_patch`.
