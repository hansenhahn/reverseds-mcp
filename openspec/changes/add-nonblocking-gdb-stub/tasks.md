## 1. Investigação (design → código)

- [ ] 1.1 Mapear `GdbStub::Poll`/`Enter` e todos os pontos que bloqueiam a `EmuThread` (handshake, espera por comando, reconexão). Verificar: lista de pontos de bloqueio documentada no design.
- [ ] 1.2 Desenhar a espera cooperativa (timeout no `Poll` ou sinalização por evento) sem quebrar handshake/`QStartNoAckMode`/reconexão. Verificar: design atualizado com a decisão.

## 2. Emulador — espera cooperativa (stub)

- [ ] 2.1 `Poll` deixa de bloquear indefinidamente enquanto o alvo está parado (timeout curto/evento) e a `EmuThread` retorna ao laço. Verificar: com gdb parado, o laço volta a chamar `handleMessages()`.
- [ ] 2.2 O laço, no estado "gdb parado", atende o canal **sem emular quadros** (ocioso, sem busy-spin). Verificar: com gdb parado, o contador de quadro não avança e a CPU é baixa.
- [ ] 2.3 Semântica do depurador preservada (breakpoint/watchpoint/single-step/handshake/reconexão). Verificar: smoke do stub (parar em breakpoint, watchpoint, step, reconectar) OK.

## 3. MCP — verificação

- [ ] 3.1 Com gdb anexado e parado: `screen_capture`, `savestate_save`, `emu_step_frame` respondem (não expiram). Verificar: smoke com o gdb anexado.
- [ ] 3.2 Fluxo copiloto: congelar frame (frame-control) → capturar → armar watchpoint → ler o código, sem desconectar o gdb. Verificar: sequência executa ponta a ponta.

## 4. Validação

- [ ] 4.1 Build do melonDS sem regressão; testes/smoke do MCP verdes. Verificar: build + `pytest`.
- [ ] 4.2 `openspec validate add-nonblocking-gdb-stub --strict` OK. Verificar: comando sem erro.
