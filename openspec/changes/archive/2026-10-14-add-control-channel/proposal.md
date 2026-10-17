## Why

O agente (MCP) precisa atuar como copiloto do emulador: injetar input, ver a tela,
salvar/restaurar estado e reagir a eventos. Hoje o único canal é o stub GDB — que
atende **um** cliente, amarra o controle ao estado de debug e não suporta binário
grande (framebuffer) nem eventos. Isso impede o copiloto de rodar junto do humano
(que também usa o gdb) e de "enxergar" o jogo.

## What Changes

- Adiciona um **servidor de controle** dentro do melonDS, em socket próprio
  (Unix domain socket por padrão; TCP opcional), **separado** do stub GDB.
- Protocolo: **JSON-RPC 2.0** com framing `Content-Length` (estilo LSP/DAP) e um
  **frame binário** dedicado para payloads grandes (framebuffer da tela).
- Métodos: `input.key`, `input.touch`, `input.release`, `input.merge`,
  `screen.capture`, `savestate.save`, `savestate.load`, `emu.pause`, `emu.resume`,
  além de **notificações** (eventos) como `event.frame` e `event.stopped`.
- O input do agente é combinado (**AND**, máscara active-low) com o input do host,
  permitindo humano e agente na mesma instância ao mesmo tempo.
- Operações que tocam o núcleo (savestate, pause) são roteadas pela fila de
  mensagens da EmuThread, mantendo a thread-safety.
- O input via `qRcmd` (monitor) permanece como caminho alternativo/compatível.

## Capabilities

### New Capabilities
- `control-channel`: canal de controle do emulador voltado ao agente — protocolo
  (framing + JSON-RPC + frame binário), métodos de input/tela/savestate/pause e
  notificações de eventos.

### Modified Capabilities
<!-- nenhuma: o stub GDB e o input via monitor não têm requisitos alterados -->

## Impact

- **Código**: novo módulo na camada de frontend (`src/frontend/qt_sdl`), reusando
  APIs existentes do núcleo (`NDS::SetKeyMask`, `NDS::TouchScreen`,
  `GPU::GetFramebuffers`, savestate) e a fila de mensagens da EmuThread. Nenhuma
  mudança no comportamento de emulação.
- **Dependências**: `nlohmann/json` (header-only) para serialização; socket via a
  abstração `Platform`. `msgpack` fica descartado nesta versão.
- **Relação**: **complementa** (não substitui) o stub GDB — controle por um canal,
  debug (breakpoints/memória/watchpoints) por outro.
- **Segurança/superfície**: socket local (Unix domain) por padrão; sem exposição
  de rede a menos que habilitado explicitamente.
