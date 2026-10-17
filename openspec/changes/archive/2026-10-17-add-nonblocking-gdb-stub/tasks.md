## 1. Investigação (design → código)

- [x] 1.1 Mapear `GdbStub::Poll`/`Enter` e onde a `EmuThread` fica presa (busy-loop em `Enter`, chamado de `ARM::GdbCheckB` dentro de `Execute`/`RunFrame`). Verificar: documentado no design.
- [x] 1.2 Decidir o mecanismo: **hook de serviço no laço do stub** (laço de pacotes fechado). Alternativa "yield ao laço" foi tentada e **revertida** (quebrou o protocolo do gdb). Verificar: decisão registrada no design.

## 2. Emulador — hook de serviço (stub)

- [x] 2.1 `Gdb::HaltService` (hook) chamado no laço de espera do stub enquanto o alvo está parado; sleep curto para não girar em falso. Verificar: o stub chama o hook e o laço não queima CPU.
- [x] 2.2 `EmuThread` registra o hook (`handleMessages()`), atendendo o canal de controle **sem emular** (a CPU segue parada). Verificar: com gdb parado, o contador de quadro não avança e o canal responde.
- [x] 2.3 Semântica do depurador preservada (handshake/registradores/breakpoint/step). Verificar: attach + ler `pc` + `stepi` + `set_breakpoint` OK.

## 3. MCP — verificação

- [x] 3.1 Com gdb anexado e parado: `screen_capture` (0,00s) e `savestate_save` (0,17s) respondem (não expiram). Verificar: smoke com o gdb anexado.
- [x] 3.2 Fluxo copiloto completo: congelar frame (frame-control) → capturar → armar watchpoint → ler o código, sem desconectar o gdb. Verificar: sequência ponta a ponta.

## 4. Validação

- [x] 4.1 Build do melonDS sem regressão; sem gdb `emu.step_frame(60)` ≈ 1,04 s (tempo real) e captura OK. Verificar: build + smoke.
- [x] 4.2 `openspec validate add-nonblocking-gdb-stub --strict` OK. Verificar: comando sem erro.
