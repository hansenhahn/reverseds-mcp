## Context

Ver `proposal.md` — Why. Hoje `screen.capture` depende do laço de emulação avançar (o
renderer software compõe no passo de quadro); com a CPU parada, a captura expira. O
'melonds' já tem a fila de mensagens da `EmuThread` e o caminho `msg_ControlCapture`
(`ControlServer::serviceCapture`). O change é no **emulador (frontend)**.

## Goals / Non-Goals

**Goals:**
- Capturar/renderizar o quadro atual com a CPU parada.

**Non-Goals:**
- Frame-step (`add-frame-control`); `render_layer` (`add-layer-render`).

## Decisions

- **Forçar a composição do quadro atual sob demanda** no caminho de captura, em vez de
  esperar o próximo passo de quadro. Alternativa descartada: ler VRAM/memória e compor à
  mão — foi o que a sessão tentou e falhou (tile base, paleta, mapeamento de banco).
- **Reusar `GPU::GetFramebuffers`**/o renderer existente (sem reimplementar composição).
- **Sem custo por quadro**: o trabalho acontece só na captura (sob demanda), conforme a
  regra de carga mínima.

## Risks / Trade-offs

- [Renderer de hardware/GL vs software] → o render sob demanda SHALL funcionar no caminho
  de software; documentar a dependência.
- [Estado parcial se chamado no meio de um passo] → a captura ocorre na `EmuThread`, num
  ponto consistente (vblank), como as demais operações de núcleo.
