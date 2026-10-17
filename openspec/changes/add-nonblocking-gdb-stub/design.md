## Context

Ver `proposal.md` — Why. O stub GDB tem duas esperas:
- `GdbStub::Poll(wait)` (`src/debug/GdbStub.cpp:291`): com `wait=true` faz
  `SocketSetBlocking(SockFd, true)` + `poll(fd, ..., -1)` → **bloqueia indefinidamente**.
- `ARM::GdbCheckA/B` (`src/ARM.cpp:38`): `GdbCheckA` chama `Enter(false, ...)` (poll
  não-bloqueante, a cada intervalo); `GdbCheckB` chama `Enter(true, ...)` (bloqueante)
  quando o alvo está parado/step. Com o gdb parado, `GdbCheckB` bloqueia a `EmuThread`
  dentro do `RunFrame()`.

Quando o gdb está anexado, o NDS usa **`InterpreterGDB`** (JIT desligado,
`NDS.cpp:115`). O laço da `EmuThread` roda `RunFrame()` → ... → `drawScreen()` →
`handleMessages()` (`EmuThread.cpp:457`). Como a `EmuThread` fica presa no `Poll`, o
`handleMessages()` não roda e o canal de controle morre. Medido: `emu.step_frame` e
`savestate` dão timeout; `screen.capture` expira; só `ping` responde.

## Goals / Non-Goals

**Goals:**
- Canal de controle responsivo com gdb anexado, **sem avançar quadros** com a CPU parada.

**Non-Goals:**
- Mudar a semântica do depurador (breakpoints/watchpoints/single-step).
- Captura-em-específico (`add-paused-capture`) — aqui é o problema de fundo.
- Performance: medida e preservada (interpreter mantém ~60 fps com gdb).

## Decisions

- **Espera cooperativa no stub.** Enquanto o alvo está parado, o `Poll` SHALL usar timeout
  curto (ou ser sinalizado por evento) e **retornar ao laço**, em vez de bloquear. O laço,
  nesse estado, **ociosamente atende `handleMessages()` sem emular** (como o branch "paused"
  já faz: `SDL_Delay` curto + `drawScreen`).
  - Alternativa descartada: capturar direto da thread de controle — remendo local (não
    resolve savestate/input) e fere o modelo "núcleo só na EmuThread".
  - Alternativa descartada: drenar mensagens do controle dentro do `Poll` — inverte
    dependência (stub → control channel).
- **Não avançar quadros com a CPU parada**, para preservar a semântica do depurador: o
  laço ocioso só atende controle.
- **Evitar busy-spin:** timeout/sleep curto na espera (CPU ociosa, não tempo do NDS).
- **Sinalização por evento** (eventfd/condição) ideal para o canal acordar a espera sem
  polling caro; o timeout curto é o fallback simples.

## Risks / Trade-offs

- [Correção do stub] mexer no `Poll`/`Enter` pode afetar handshake, `QStartNoAckMode`,
  reconexão. → testes no stub (handshake, breakpoint/watchpoint, step) antes de concluir.
- [Laço ocioso consumindo CPU] → timeout/sleep curto.
- [Regressão de tempo real] → medido: interpreter com gdb mantém ~60 fps; a mudança não
  toca o caminho quente (só o estado "parado").
- [Ordem com `add-frame-control`] `step_frame` com gdb anexado passa a funcionar; garantir
  que parar o núcleo por frame-step não conflita com o stub (nota na doc).
