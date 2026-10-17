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

- **Hook de serviço no stub (implementado).** O laço de espera do stub
  (`GdbStub::Enter`) **permanece fechado** e, enquanto o alvo está parado, chama um hook
  (`Gdb::HaltService`, um `std::function`) registrado pelo frontend; a `EmuThread` o
  registra para processar as mensagens pendentes do canal de controle. O stub dorme um
  pouco por iteração (`Platform::Sleep`) para não girar em falso. Como o laço de pacotes
  do gdb **não é intercalado** com o laço de quadro, o protocolo do gdb fica intacto.
  - Alternativa descartada: **capturar direto da thread de controle** — remendo local (não
    resolve savestate/input) e fere o modelo "núcleo só na EmuThread".
  - Alternativa descartada: **drenar mensagens do controle dentro do `Poll`** — inverte
    dependência (stub → control channel).
  - Alternativa descartada (tentada): **yield ao laço** (o `Enter` retorna; `Execute`/
    `RunFrame` dão bail; a EmuThread atende o canal e re-entra). Fez o canal de controle
    responder, **mas quebrou o protocolo do gdb** (falha na leitura de registradores/`qXfer`)
    porque intercala o laço de quadro entre os pacotes do gdb durante o handshake. Revertida.
- **Não avançar quadros com a CPU parada**, para preservar a semântica do depurador: o
  hook só bombeia o canal de controle, não emula.
- **Evitar busy-spin:** `Platform::Sleep` curto na espera (CPU ociosa, não tempo do NDS).

## Risks / Trade-offs

- [Acoplar o stub ao frontend via callback] → é um `std::function` registrado pela
  `EmuThread`; o `src/debug/` não conhece o frontend, só chama o hook. Menor mal que
  intercalar o laço (que quebrou o protocolo).
- [Segurança de re-entrância] → o hook roda na **mesma** thread de emulação (dentro do
  stub), então `handleMessages()` é chamado no thread correto; a CPU está parada (não emula).
- [Ordem com `add-frame-control`] `step_frame` com gdb anexado passa a ser atendido pelo
  caminho do hook (a CPU está parada por gdb, então não avança quadros — nota na doc).
- [Regressão de tempo real] não toca o caminho quente; medido sem gdb: `step_frame(60)` ≈
  1,04 s (tempo real) inalterado.

