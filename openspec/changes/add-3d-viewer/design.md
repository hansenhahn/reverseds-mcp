## Context

Ver `proposal.md` — Why. Estado atual:

- `OAMViewerDialog` (`src/frontend/qt_sdl/OAMViewerDialog.{h,cpp}`) já estabelece o
  padrão: diálogo aberto pelo menu, `QTimer` de refresh, `freeze` que pausa a
  EmuThread (`emuPause`/`emuUnpause`), widgets de grade/preview e painel de
  detalhes. É a referência a imitar.
- **Quick win, sem dependência:** o viewer lê o core in-process e não depende do
  canal/MCP nem do `add-3d-inspection`. `RenderPolygonRAM` é finalizado no VBlank e
  permanece com o **último frame completo** entre VBlanks, então um freeze lê uma
  lista completa. O snapshot one-shot no VBlank (estado+polígonos+textura do mesmo
  frame) será compartilhado com o inspection depois.
- `GPU3D` é público no `GPU`; `RenderPolygonRAM[0..RenderNumPolygons)` é a lista
  renderizada e `Vertex::FinalPosition[2]` a posição de tela.
- O renderer da camada 3D já existe no emulador; não reimplementar.
- Texturas: `GPU3D_Texcache` já decodifica formatos; reusar.

## Goals / Non-Goals

**Goals:**

- Janela única de viewers com abas (OAM migrado + 3D), estilo No$gba.
- Ver o frame 3D e sobrepor os polígonos com `id` e seleção.
- Lista de polígonos + vértices com `screenpos (x/y/z/w)` e atributos.
- Preview da textura do polígono selecionado.
- Painel de estado (matrizes, viewport, fog/toon/edge, `GXStat`, níveis de FIFO).
- Freeze/refresh thread-safe no padrão do viewer de OAM.
- Ajudar a **localizar** um elemento na tela (para reposicionar depois).
- **Validar** os dados 3D visualmente antes de expô-los via MCP.

**Non-Goals:**

- Escrever/reposicionar/poke (change `add-3d-edit`, posterior).
- Edição de textura.
- Reimplementar rasterização; usar o renderer do emulador.
- Substituir o `render_layer`/captura do MCP.

## Decisions

- **Janela de viewers com abas.** Novo `ViewerTabsDialog` (`QDialog` com
  `QTabWidget`), aberto pelo menu, no estilo do "VRAM Viewer" do No$gba. Aba OAM
  (migrada) e aba 3D; futuras abas (BG/paleta) plugam no mesmo container.
  Alternativa descartada: manter diálogos separados (foi o pedido mudar).
- **Migração do OAM de baixo risco.** Embutir o `OAMViewerDialog` atual como página
  da aba OAM (reparent para `Qt::Widget`) nesta versão; refatorar para uma
  `OAMViewerPage` dedicada só se necessário, num follow-up. Preserva seleção/
  preview/detalhes/freeze e evita regressão. Alternativa descartada: reescrever o
  OAM agora.
- **Página 3D como `QWidget`.** `ThreeDViewerPage` é um widget de aba (não um
  diálogo), para plugar no `QTabWidget`.
- **Reusar o padrão do `OAMViewerDialog`.** Mesmo ciclo de vida de refresh
  (`QTimer`) e freeze pausando a EmuThread. Alternativa descartada: um dock/overlay
  na tela do jogo (mais invasivo).
- **Ler o core direto no frontend (in-process), não via canal de controle.** O
  viewer é do fork e roda no mesmo processo; como o OAM viewer, lê o `GPU3D` no
  refresh. O canal/MCP ficam para automação. Alternativa descartada: fazer o
  viewer consumir o control channel (latência e acoplamento desnecessários).
- **Freeze = pausa + leitura do último frame finalizado.** Congelar pausa a
  EmuThread e lê `RenderPolygonRAM` (finalizado no último VBlank), então a lista de
  polígonos é completa; o painel de estado reflete o ponto de pausa. O snapshot
  one-shot no VBlank (estado+polígonos+textura do mesmo frame) entra quando o
  inspection chegar e é compartilhado. Descongelar retoma. Rodando, o timer
  atualiza como o OAM viewer.
- **Preview de textura do polígono selecionado.** Reusa o decoder existente
  (`GPU3D_Texcache`) e exibe a textura (`TexParam`/`TexPalette`) do polígono; sem
  decodificador novo no frontend.
- **Overlay de `RenderPolygonRAM`.** Desenha contorno e `id` de cada polígono
  sobre o frame 3D; a seleção (lista ou clique) destaca o polígono e mostra os
  vértices com `FinalPosition`. Limite de polígonos desenhados para não pesar.
- **Fundo = framebuffer do renderer.** Usa o frame do renderer de software (como
  a captura); se indisponível (renderer OpenGL), mostra só o wireframe/overlay,
  com aviso. Alternativa descartada: forçar troca de renderer.
- **Sem mudança de núcleo.** Se a leitura duplicar demais a lógica do inspection,
  extrair um helper read-only do `GPU3D` num follow-up — não neste change.

## Risks / Trade-offs

- [Renderer OpenGL sem framebuffer na CPU] → fallback wireframe/overlay + aviso.
- [Regressão no OAM ao migrar] → embutir como página preservando o comportamento e
  validar seleção/preview/detalhes/freeze antes/depois.
- [Refresh frequente] → timer moderado (ex.: 10–20 Hz) enquanto roda; congelado,
  só repaint do snapshot. Copiar frame 256×192×4 (~192 KB)/refresh é barato, mas
  não precisa de 60 Hz.
- [Frame × lista de polígonos] → `RenderPolygonRAM` é do último VBlank (frame
  completo); o painel de estado é do ponto de pausa. O snapshot exato no VBlank
  vem com o inspection e elimina a diferença residual.
- [Textura sem preview/formato não suportado] → mostra aviso e mantém o resto do
  viewer; o decoder é o existente do renderer (`GPU3D_Texcache`).
- [Muitos polígonos pesam o overlay] → limite/decimação e desenho só do contorno.
- [Leitura concorrente enquanto roda] → mesmo modelo do OAM viewer; para análise
  fina, congelar.
- [Confundir polígono renderizado com a origem] → o viewer localiza na tela; a
  causa/origem continua no trace/ASM.

## Migration Plan

Aditivo e isolado no frontend; **pode ser o primeiro** (quick win). Nova ação de
menu; sem ação = comportamento atual. Validar com build do fork e inspeção manual
numa cena 3D do KH (frame, overlay, seleção, textura, painel) com o jogo
rodando/parado. O inspection/MCP entram depois e reusam o modelo (e o snapshot no
VBlank).

## Open Questions

- Wireframe vs. contorno preenchido translúcido — decidir na implementação.
- Clique no canvas para selecionar polígono (hit-test de bbox) — desejável;
  confirmar custo.
- Extrair um snapshot read-only compartilhado (`GPU3D`) quando o inspection
  entrar, para viewer e canal lerem o mesmo frame.
