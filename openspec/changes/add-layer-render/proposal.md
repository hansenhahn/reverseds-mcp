## Why

A sessão de RE tentou identificar onde estava o texto compondo BG/OBJ/3D **à mão** no
script (tile base, paleta, stride, mapeamento de banco) e **falhou** — gerou listras e a
"paleta 15 fantasma". O certo é usar o **renderer do próprio melonDS como oráculo**:
renderizar uma camada isolada e olhar o que o emulador realmente compõe.

## What Changes

- `video.render_layer`: renderiza uma **camada específica** — engine (A/B) × `BG0-3`/`OBJ`/3D
  — e devolve o quadro resultante.
- O render SHALL usar o renderer do emulador (não uma reimplementação).
- Emulador (fork) + tool MCP correspondente.
- **Não altera o comportamento de emulação**; custo só sob demanda.

## Capabilities

### New Capabilities
- `video-render`: render de uma camada pelo renderer do emulador.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- melonDS: render de camada única no frontend (reuso do renderer de software/GPU).
- MCP: tool fina que pede o render e salva o quadro.
