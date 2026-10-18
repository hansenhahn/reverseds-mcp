## Context

Ver `proposal.md` — Why. O melonDS compõe os quadros internamente (`GPU`, renderer de
software/GPU); o canal de controle já entrega o framebuffer **composto**. Falta expor o
render de **uma** camada. O change é no **emulador (frontend)**, com uma tool fina no MCP.

## Goals / Non-Goals

**Goals:**
- Render de uma camada isolada (engine × BG/OBJ/3D) pelo renderer do emulador.
- Não executar código da CPU nem alterar o quadro exibido (custo só sob demanda).
- Nunca travar o emulador (a sessão de RE depende dele rodando/interativo).

**Non-Goals:**
- Reimplementar composição no MCP (o que falhou na sessão).
- Editar/enviar camadas de volta ao emulador.

## Decisions

- **Usar o renderer do melonDS** (software) restrito a uma camada — o oráculo é o que o
  emulador exibe. Alternativa descartada: compor BG/OBJ/3D no script.
- **Re-render off-loop** (`video.render_layer`): reproduz a sequência por linha do
  `StartScanline`/`StartHBlank` (`UpdateRegistersPreDraw` → `DrawScanline` → `DrawSprites`
  → `UpdateRegistersPostDraw`, com a passada de *reset* em `VCount==262`), só desenhando —
  sem tocar CPU/DMA/timers/IRQ. Assim um frame congelado pode ser inspecionado por camada.
- **Isolado**: a saída composta vai para **buffers de rascunho**
  (`SoftRenderer::SetExternalRenderTarget`); o `Framebuffer`/`BackBuffer` vivo **nunca** é
  tocado (sem `SwapBuffers`).
- **Filtro por camada**: `GPU2D::RenderMask` (bit0-3 = BG0-3, bit4 = OBJ) gate no renderer
  2D de software.
- **Sem deadlock na thread 3D**: com o jogo pausado a thread de render 3D não produz
  scanlines; `SoftRenderer3D::ExternalScanlineRead` pula a espera do semáforo (o último 3D
  já está no `ColorBuffer`, que é o que se quer para um frame congelado).
- **Estado restaurado por RAII** e **pilha de pausa balanceada** (`emuPause` + `emuUnpause`
  incondicional) — o emulador continua rodando (ou pausado) como estava.

## Risks / Trade-offs

- [Travar o emulador] → **resolvido**. A primeira versão travava (pausa desbalanceada + a
  espera do semáforo da thread 3D). Agora: re-render isolado + RAII + pausa balanceada.
  Validado rodando e pausado, com N renders repetidos, sem congelar.
- [GPU vs software] → alvo é o renderer de software (o mesmo da captura); GPU fica como
  extensão futura.
- [Camadas que dependem de estado por-frame] → combinar com `emu_pause`/`emu_step_frame`
  (`add-frame-control`) para um frame determinístico.
- [A outra engine aparece como backdrop] → ao isolar uma camada, a outra engine desenha só
  o seu backdrop (não o conteúdo). Aceitável para "onde está este conteúdo"; documentado.
