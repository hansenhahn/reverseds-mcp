## 1. Janela de viewers com abas

- [x] 1.1 Criar `ViewerTabsDialog.{h,cpp}` (`QDialog` com `QTabWidget`), no estilo
  do "VRAM Viewer" do No$gba, com abas OAM e 3D. Verificar: build e janela
  abre/fecha sem crash.
- [x] 1.2 Trocar a ação de menu para abrir a janela de viewers (em vez do
  `OAMViewerDialog` isolado), habilitando só com jogo carregado. Verificar: menu
  abre a janela na aba correta; sem jogo fica desabilitado.

## 2. Migração do OAM

- [x] 2.1 Embutir o `OAMViewerDialog` atual como página da aba OAM (reparent para
  `Qt::Widget`) preservando seleção, preview, detalhes e freeze. Verificar:
  comparar comportamento antes/depois (grid, preview, freeze, engine A/B).
- [x] 2.2 Garantir que fechar a janela de viewers encerra o timer/pausa do OAM sem
  vazar nem deixar a EmuThread pausada. Verificar: abrir/fechar várias vezes e
  confirmar que o jogo não fica pausado.

## 3. Página 3D — estrutura

- [x] 3.1 Criar `ThreeDViewerPage.{h,cpp}` (`QWidget`) com canvas, lista de
  polígonos, painel de detalhes/estado e preview de textura; adicionar como aba.
  Verificar: build e aba 3D abre sem crash.
- [x] 3.2 Adicionar os arquivos ao `CMakeLists.txt`. Verificar: build.

## 4. Snapshot e freeze

- [x] 4.1 Implementar o snapshot de estado + `RenderPolygonRAM` + índices de
  textura no refresh/freeze: congelar pausa a EmuThread e lê a lista **finalizada
  no último VBlank** (frame completo); o painel de estado é do ponto de pausa.
  Descongelar retoma, reusando o padrão do OAM viewer. Verificar: congelar
  estabiliza overlay/lista; descongelar volta a atualizar.

## 5. Frame + overlay

- [x] 5.1 Renderizar o fundo com o frame do renderer de software (top screen) e
  desenhar o contorno/`id` dos polígonos; fallback wireframe quando o framebuffer
  não estiver disponível. Verificar: overlay alinhado ao frame numa cena 3D.
- [x] 5.2 Seleção sincronizada com o overlay (lista → destaque; opcional clique no
  canvas via bbox). Verificar: selecionar destaca o polígono correto.

## 6. Lista, vértices, estado e textura

- [x] 6.1 Lista de polígonos (`id`, tipo, atributos, translúcido, bbox de tela).
  Verificar: lista coerente com o overlay.
- [x] 6.2 Mostrar os vértices do polígono selecionado com `screenpos (x/y/z/w)` e
  cor, e o painel de estado (matrizes/viewport/fog/toon/edge/`GXStat`/FIFO).
  Verificar: valores coerentes com o frame; quando o inspection existir, cruzar
  com `gpu3d_state`/`gpu3d_polygons`.
- [x] 6.3 Preview da textura do polígono selecionado, reusando o decoder existente
  (`GPU3D_Texcache`, `TexParam`/`TexPalette`). Verificar: textura exibida
  coerente com o No$gba; quando o inspection existir, cruzar com
  `gpu3d_texture_dump`.

## 7. Validação

- [x] 7.1 Build `Release` (JIT off, GDB on) sem regressão. Verificar:
  `cmake --build build -j` conclui.
- [x] 7.2 Inspeção manual numa cena 3D do KH: abas OAM/3D, frame + overlay +
  seleção + textura + painel coerentes; com o jogo rodando e congelado.
  Verificar: nenhum crash, OAM sem regressão e comportamento do emulador inalterado.
- [x] 7.3 `openspec validate add-3d-viewer --strict` verde.
- [ ] 7.4 Verificar custo do viewer: timer moderado, congelado sem trabalho por
  quadro, e nenhum impacto perceptível no jogo com a janela aberta. Verificar:
  frame time estável antes/depois de abrir a janela.
