## Why

O canal de controle hoje só expõe `input.key` (segura) e `input.release` (solta). Para
automatizar transições de tela (ex.: **Start → B** para re-renderizar o HUD, navegar listas
de menu), o agente precisa montar na mão uma sequência de chamadas com esperas — verboso,
frágil, e impossível de intercalar quando um `debug_continue`/`debug_resume` está no controle.

Este change adiciona **macros de input** (tap e sequência) ao MCP, para o agente disparar
transições de tela de forma confiável.

## What Changes

- Nova tool `input_tap(mask, ms)`: pressiona a(s) tecla(s) da máscara, aguarda `ms`, solta.
- Nova tool `input_touch_tap(x, y, ms)`: toca `(x, y)` na **tela de baixo** (touch), aguarda
  `ms`, solta — para jogos **touch-only**.
- Nova tool `input_sequence(steps)`: executa uma lista ordenada de passos
  `{mask|touch, ms, after_ms}` — segura um botão (**ou** um toque), espera, solta, espera —
  podendo **intercalar** botões e toques.
- Implementado no **MCP (Python)**, reutilizando `input.key` / `input.touch` / `input.release`.
- **Nada muda no emulador.**

## Capabilities

### Modified Capabilities
- `mcp-control-tools`: adiciona as macros de input (tap e sequência).

## Impact

- Apenas o MCP: um helper de domínio + duas tools. Sem mudança no melonDS.
- Sem custo por quadro (executa fora da EmuThread; é o agente que chama).
- Depende do canal de controle já existente.
