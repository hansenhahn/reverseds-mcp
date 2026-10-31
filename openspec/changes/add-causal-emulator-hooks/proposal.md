## Why

A primeira metade da Onda 1 (breakpoint condicional/comandos + backtrace) destravou a
causalidade no MCP, mas ainda faltam três buracos no runtime: **cold reset** determinístico
(a tela só é montada na primeira abertura), **hits sem parar** (o agente precisa interromper
a cada evento para saber o que passou) e **escritas de DMA/VRAM** (watchpoint de CPU não vê
DMA). Sem isso, o fluxo "arma → roda → descobre quem fez" continua manual em casos comuns.

## What Changes

- **Cold reset** (`emu.reset` no canal): reinicia a máquina via `EmuThread::emuReset`,
  preservando breakpoints/watchpoints do stub. Com o gdb conectado, a CPU fica parada no
  vetor de reset até `debug_resume`; sem gdb, o emulador volta a rodar.
- **Hit log** (`gdb.hits.start/stop/read/clear`): o stub registra hits de breakpoint e
  watchpoint em um ring buffer **sem parar a execução**, com contagem de descartados.
  Consultável por core (`arm9`/`arm7`).
- **Watchpoint de DMA/VRAM**: write/access watchpoints existentes SHALL disparar também
  quando um DMA escreve na faixa vigiada. Com o hit log ligado, o hit é registrado (com o
  PC da instrução que programou o DMA) sem parar; sem o log, o stub para como um watchpoint
  normal.
- **MCP**: novas tools `emu_reset`, `hit_log_start`, `hit_log_stop`, `hit_log_read` e
  `hit_log_clear`; `hit_log_read` devolve `pc`/`addr` em hex e `kind` legível
  (`breakpoint`, `write`, `read`, `access`, `dma-write`).

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `control-channel`: adiciona `emu.reset` e `gdb.hits.*`; DMA passa a consultar os
  watchpoints de escrita/acesso.
- `mcp-control-tools`: adiciona `emu_reset`.
- `mcp-debug-tools`: adiciona as tools de hit log e o cenário de watchpoint de DMA.

## Impact

- Emulador: `src/debug/GdbStub.{h,cpp}` (ring de hits, check de DMA),
  `src/ARM.{h,cpp}` (check de DMA no core), `src/NDS.{h,cpp}` (ponte), `src/DMA.cpp`
  (span de destino), `src/frontend/qt_sdl/ControlServer.{h,cpp}` (`emu.reset`/`gdb.hits.*`).
- MCP: `tools/control.py` (`emu_reset`), `tools/debug.py` (hit log), testes.
- Sem custo por quadro; o check de DMA ocorre por transferência/slice, não por unidade.
