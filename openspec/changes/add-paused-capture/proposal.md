## Why

`screen_capture` **falha com a CPU parada** ("timed out"): o renderer do melonDS precisa do
laço de emulação avançando para compor o quadro. Isso quebra o fluxo "pausar e olhar" — o
agente congela um frame (frame-control) e então não consegue capturá-lo. Sem isso, a
observação do frame exato fica cega.

## What Changes

- A captura SHALL funcionar com a CPU **parada**, renderizando o framebuffer atual sob
  demanda (ou via um `render_frame()` explícito).
- A captura NÃO SHALL depender de a emulação avançar quadros nem expirar por isso.
- Emulador (fork): caminho de render sob demanda; MCP: remove/atualiza o hint atual de
  "CPU haltada" (que deixa de ser um erro).
- **Não altera o comportamento de emulação.**

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `control-channel`: a captura passa a funcionar com a CPU parada.

## Impact

- melonDS: renderização sob demanda no caminho de captura (frontend), sem custo por quadro.
- MCP: a tool de captura deixa de tratar "CPU parada" como erro.
