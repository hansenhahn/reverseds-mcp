## 1. Emulador — cold reset

- [x] 1.1 Adicionar `emu.reset` ao `ControlServer`, chamando
  `instance->getEmuThread()->emuReset()` e retornando `{ok:true}`. Verificar: chamada manual
  no socket reinicia e não derruba a conexão.
- [x] 1.2 Validar que BPs/WPs sobrevivem ao reset e que, com gdb anexado, a CPU fica parada no
  vetor até `debug_resume`. Verificar: teste real com um BP armado.

## 2. Emulador — hit log

- [x] 2.1 Adicionar `HitRecord`/ring (`std::deque`, mutex, flag atômica) ao `GdbStub`, com
  `StartHitLog/StopHitLog/ClearHits/ReadHits`. Verificar: build e teste unitário do ring
  (capacidade, dropped, clear).
- [x] 2.2 Em `CheckBkpt`/`CheckWatchpt`, com o log ligado, registrar e retornar
  `CheckNoHit` (sem parar). Verificar: hit log real com breakpoint frequente.
- [x] 2.3 Expor `gdb.hits.start/stop/read/clear` no `ControlServer` por core, com
  `pc`/`addr`/`kind` e `dropped`. Verificar: chamadas manuais no socket.
- [x] 2.4 Adicionar as tools MCP `hit_log_start/stop/read/clear` com formatação hex/kind e
  erros claros. Verificar: testes com canal fake; descoberta no `list_tools`.

## 3. Emulador — watchpoint de DMA/VRAM

- [x] 3.1 Adicionar `GdbStub::CheckDmaWatchpt(addr, len, program_pc, ...)` (write/access) e
  `ARM::GdbCheckDmaWrite`/`NDS::GdbCheckDmaWrite`; registrar `kind="dma-write"` no hit log ou
  parar quando o log estiver desligado. Verificar: build.
- [x] 3.2 Em `DMA::Run9/Run7`, calcular a faixa de destino efetivamente escrita no slice e
  chamar o check (somente se houve transferência). Verificar: smoke real com VRAM.
- [x] 3.3 MCP: documentar/testar o cenário de watchpoint de VRAM preenchida por DMA
  (`set_watchpoint` + `hit_log_*`). Verificar: teste de tool e smoke real.

## 4. Documentação

- [x] 4.1 Atualizar a skill com `emu_reset`, `hit_log_*` e o fluxo DMA→watchpoint.
  Verificar: skill cita as tools e o cuidado com o PC do programador.

## 5. Validação

- [x] 5.1 MCP: `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-causal-emulator-hooks --strict` verdes.
- [x] 5.2 Emulador: build `-j 1` sem regressão.
- [x] 5.3 Smoke real: reset com BP (BP preservado, PC na entrada de boot determinística); hit log de breakpoint sem
  parar; DMA de VRAM com watchpoint/log. Verificar: saídas coerentes.

> Validado em 2026-10-30: fork buildado com `-j 1`; `pytest` (130), `pyright`,
> `lint-imports` e `openspec validate --strict` verdes. Smoke real (KH): reset com BP
> preservado e PC estável em `0x02000800`; hit log registrou breakpoint sem parar; DMA em
> `0x06207000` gerou hits `dma-write` com PC `0x01ff860c` (e o stop, com o log desligado,
> caiu no mesmo PC).
