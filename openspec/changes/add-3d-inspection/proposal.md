## Why

A depuração 3D está cega. Hoje o canal expõe a **imagem** da camada 3D
(`video.render_layer` com `layer=3d`) e o IO 2D, mas não o que o pipeline 3D
está fazendo: matrizes, viewport, fog/toon/edge, níveis das filas, os polígonos
gerados e, principalmente, **a fila de comandos GXFIFO** (quem enfileirou, em
que ordem e com que profundidade). Sem isso, bugs de cena/HUD 3D viram
adivinhação por screenshot e leitura de memória.

Este change é o pré-requisito de debug 3D; o renderer continua sendo o oracle da
imagem, não uma reimplementação. Um dos usos é **localizar elementos na tela**
(polígonos/vértices) para depois reposicioná-los — por isso o dump de polígonos
inclui a **posição final de tela** por vértice.

## What Changes

- **Canal de controle (emulador):**
  - `3d.state`: estado decodificado do core 3D (enable, DISP3DCNT/GXStat, níveis
    de FIFO, matrix mode, matrizes projeção/posição/vetor/textura/clip, viewport,
    alpha, fog, toon/edge, contadores de vértices/polígonos).
  - `3d.polygons`: dump dos polígonos do frame renderizado (atributos + vértices
    com posição/cor/texcoord, com limite e paginação simples).
  - `3d.textures`: lista as texturas usadas pelos polígonos do frame
    (`TexParam`/`TexPalette` → formato/tamanho/paleta) e `3d.texture` decodifica
    uma textura para RGBA (frame binário), reusando o decoder existente do
    renderer (`GPU3D_Texcache`), no espírito do viewer de textura do No$gba.
  - `3d.gxfifo.start/read/stop`: trace em ring das entradas enfileiradas no
    GXFIFO (`cmd`, `param`, `pc`, `frame`, profundidade `fifo`), com **decode
    legível no `read`** (`begin_vtxs`, `mtx_restore`, `texcoord`, `vtx`,
    `end_vtxs`, …), inspirado na aba 3D/RE do No$gba.
- **Sincronização com o frame (não com pausa no meio):** `3d.state`,
  `3d.polygons` e `3d.textures` observam o **frame completo**. O snapshot é
  tirado no **VBlank/fim de frame** (onde `RenderPolygonRAM` é finalizado), sob
  demanda, para o frame e a lista de polígonos serem sempre coerentes.
- **MCP:** tools `gpu3d_state`, `gpu3d_polygons`, `gpu3d_textures`,
  `gpu3d_texture_dump`, `gxfifo_trace_start`, `gxfifo_trace_read`,
  `gxfifo_trace_stop`. O dump de textura é salvo em PNG em `/out`.
- **Custo:** hook O(1) no enfileiramento, só ativo quando a trace está ligada;
  zero custo por quadro sem assinante. Snapshot de estado/polígonos/texturas é
  one-shot no VBlank quando pedido (não por quadro).

## Capabilities

### New Capabilities
- `mcp-3d-tools`: tools de inspeção 3D (estado, polígonos, texturas e trace
  GXFIFO).

### Modified Capabilities
- `control-channel`: adiciona `3d.state`, `3d.polygons`, `3d.textures`,
  `3d.texture` e `3d.gxfifo.*`.

## Impact

- Emulador: `src/NDS.h` (callback `OnGXCommand`), `src/GPU3D.cpp` (hook no
  caminho de escrita do GXFIFO + snapshot no VBlank), `src/GPU3D_Texcache.*`
  (reuso do decode de textura), `src/frontend/qt_sdl/ControlServer.{h,cpp}`
  (métodos, ring, mutex, frame binário).
- MCP: `tools/three_d.py` (novo), registro em `tools/server.py`, testes; PNG de
  textura via `PIL` (já usado em `screen_capture`).
- Não altera o comportamento de emulação; nenhum caminho novo de renderização.
- Não inclui (fica para follow-up): streaming por quadro e edição de textura.
- A **UI** de viewer 3D fica no `add-3d-viewer` (H7). Ele pode vir **primeiro**
  (quick win, lê o core in-process) e este change reusa o modelo/snapshot depois.
