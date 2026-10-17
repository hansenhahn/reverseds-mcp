## Why

Quando o gdb anexa, a `EmuThread` fica **parkada dentro do stub**: `GdbStub::Poll(wait=true)`
bloqueia no `recv`, então o `handleMessages()` (no fim do laço) **nunca roda**. Consequência
medida: com o alvo haltado, **todo** o canal de controle trava — `emu.step_frame` e
`savestate.save` dão **TIMEOUT** (5 s de cliente), `screen.capture` **expira** (2 s); só
`ping` responde (não usa a EmuThread).

Ou seja, hoje os dois canais — **controle** e **debug** — são **mutuamente exclusivos**: o
agente não consegue depurar e observar ao mesmo tempo. Isso invalida o copiloto
("contexto + valores reais") e é a raiz de vários atritos da sessão de RE
("debug conectado = CPU parada", "canal desincroniza", "screen_capture timed out").

## What Changes

- Enquanto o stub está com o alvo **haltado**, a `EmuThread` SHALL **voltar ao laço** e
  atender o canal de controle, em vez de bloquear no `Poll` — **sem avançar quadros**.
- Com o gdb anexado (parado **ou** rodando), as operações de controle (captura, savestate,
  input, frame-step) SHALL funcionar, sem o agente precisar desconectar o debugger.
- Emulador (fork): `GdbStub::Poll`/`ARM::GdbCheck` cooperativos com o laço.
- **Não altera a emulação** e **não altera a semântica do depurador**
  (breakpoints/watchpoints/single-step intactos); desempenho preservado (medido: a
  interpreter com gdb mantém o tempo real — ~60 fps).

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `control-channel`: o canal de controle permanece responsivo com o debugger anexado.

## Impact

- melonDS: mudança no caminho de espera do stub (`GdbStub`/`ARM::GdbCheck`), não no núcleo
  de emulação. Sem custo por instrução adicional (a mudança afeta só o estado "parado").
- MCP: nada a mudar — as tools passam a responder com o gdb anexado (hoje dão timeout).
- Substitui/reenquadra `add-paused-capture` (que mirava só a captura e num caminho que não roda).
