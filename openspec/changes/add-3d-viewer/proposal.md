## Why

O `add-3d-inspection` deixa o estado/polígonos/trace 3D legíveis por tools, mas a
depuração continua textual: é difícil **ligar o que está na tela ao polígono**
(qual elemento é qual, onde ele está em coordenadas de tela). O viewer de OAM já
mostrou que um diálogo Qt com freeze/refresh resolve isso bem para sprites; falta
o equivalente 3D.

Um dos objetivos é localizar um elemento na tela para depois reposicioná-lo. Este
change entrega a **leitura visual** (frame + overlay + seleção); a escrita
(reposicionar/poke) é um change posterior.

**Este é o quick win e pode vir primeiro.** O viewer lê o core in-process (como o
viewer de OAM), então não depende do `add-3d-inspection`/MCP para existir: ele
serve justamente para **validar/inspecionar** os dados 3D (polígonos, `screenpos`,
texturas) antes de expor tudo pelo canal. O inspection depois reusa esse modelo.

## What Changes

- **Janela de viewers com abas (estilo No$gba "VRAM Viewer")**: novo diálogo com
  `QTabWidget`; o **OAM viewer** é migrado para a primeira aba e o **3D** vira a
  segunda. O menu passa a abrir essa janela de viewers.
- **Página OAM (migração)**: o conteúdo atual do `OAMViewerDialog` vira a aba OAM,
  preservando seleção/preview/detalhes/freeze. Sem regressão de comportamento.
- **Página 3D (`ThreeDViewerPage`)**: frame 3D renderizado + overlay de polígonos
  (contorno/`id`) com seleção; lista de polígonos e vértices com
  `screenpos (x/y/z/w)`; preview da textura do polígono selecionado.
- **Painel de estado**: matrizes (projeção/posição/vetor/textura/clip), viewport,
  fog/toon/edge, `GXStat` e níveis de FIFO.
- **Thread-safe**: freeze pausa a EmuThread e lê a lista finalizada no último
  VBlank; refresh por timer moderado (como o OAM viewer).

## Capabilities

### New Capabilities
- `melonds-viewers`: janela de viewers com abas (OAM migrado + 3D) e o conteúdo
  do viewer 3D (frame, overlay, seleção, textura, estado).

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Emulador (frontend): `src/frontend/qt_sdl/ViewerTabsDialog.{h,cpp}` (novo),
  `src/frontend/qt_sdl/ThreeDViewerPage.{h,cpp}` (novo),
  `src/frontend/qt_sdl/OAMViewerDialog.{h,cpp}` (virar página/embutir),
  `Window.{h,cpp}` (menu/ação), `CMakeLists.txt`.
- **Não depende** de `add-3d-inspection`/MCP: lê o core in-process e reusa o
  decoder de textura (`GPU3D_Texcache`). O inspection reaproveita o modelo e pode
  extrair o snapshot compartilhado depois.
- Não altera o comportamento de emulação; não escreve no core.
- Não inclui: edição/reposição (change posterior) e outras abas (BG/paleta ficam
  para os changes H1–H3).
