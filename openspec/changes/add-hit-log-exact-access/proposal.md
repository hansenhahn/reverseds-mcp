## Why

O hit log atual registra `{pc, addr, kind}`. Na prática:

- o `pc` pode ser a instrução **seguinte** (ARM `+4`), não a que acessou;
- não há largura (`8/16/32`), então dois acessos de bytes na mesma palavra são
  indistinguíveis;
- um `swpb`/RMW dispara read watchpoint e parece consumidor, mas é o produtor;
- o hit de DMA grava o endereço **do watchpoint**, não o destino real.

Isso leva a conclusões erradas de causalidade (“quem leu”/“quem escreveu”) e retrabalho.

## What Changes

- **Emulador:** `HitRecord` ganha `pc_fault`, `width`, `rmw`; `pc`/`addr` continuam
  (compatibilidade). `CheckWatchpt` recebe a largura e o PC faulting; `ARM.cpp` calcula o PC
  real (`R[15] - (thumb ? 2 : 4)`) e passa a largura do acesso. O hit de DMA grava o destino
  real e o `len`.
- **Canal:** `gdb.hits.read` inclui `pc_fault`, `width` e `rmw`.
- **MCP:** `hit_log_read` formata `pc_fault`, `fault_pc_symbol`, `access_addr`, `width` e
  `rmw`; `rmw` é derivado de um par read+write no mesmo `pc_fault`/`access_addr` quando o
  stub não o informa. `pc`/`addr` continuam.
- **Sem mudança** no caminho de stop dos watchpoints.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities

- `control-channel`: o payload do hit log ganha os campos de acesso exato.
- `mcp-debug-tools`: `hit_log_read` expõe/deriva os campos e anota o PC faulting.

## Impact

- Emulador: `src/debug/GdbStub.{h,cpp}`, `src/ARM.{h,cpp}`, `src/frontend/qt_sdl/ControlServer.cpp`.
- MCP: `tools/debug.py` (`_hit_list`), testes.
- Exige rebuild do emulador.
