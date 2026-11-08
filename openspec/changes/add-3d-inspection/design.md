## Context

Ver `proposal.md` — Why. Estado atual relevante:

- `video.render_layer` já renderiza `layer=3d` (engine A) usando o renderer do
  emulador; `video_state`/`io_read` cobrem só o IO 2D.
- O canal já tem traces baseados em `TraceRing` + mutex + hook na EmuThread
  (`cart.*`, `dma.*`); o `dma.trace` usa eventfd/batches, mas traces de VRAM por
  DMA já fornecem o padrão de ring.
- `GPU3D` expõe publicamente o estado que interessa (matrizes, viewport, fog,
  toon/edge, `GXStat`, `CmdFIFO`/`CmdPIPE`/`CmdStallQueue`, `VertexRAM`,
  `PolygonRAM`, `RenderPolygonRAM`) e o caminho de escrita do GXFIFO é
  `GPU3D::WriteToGXFIFO`, chamado por CPU e DMA via `NDS::ARM9Write32`.
- `ControlServer` roda em thread própria e já acessa `instance->getNDS()`; leituras
  que dependem de estado consistente pausam a EmuThread (`emuPause`/`emuUnpause`).
- `GPU3D::VBlank()` **finaliza** `RenderPolygonRAM` (ordena, define
  `RenderNumPolygons`) e só depois troca `CurRAMBank`. É o ponto consistente do
  frame — melhor que pausar no meio.
- Texturas 3D: cada polígono carrega `TexParam`/`TexPalette`; os texels vivem na
  VRAM de textura e o renderer já decodifica via `GPU3D_Texcache`
  (`ConvertBitmapTexture`, `ConvertCompressedTexture`, `ConvertAXIYTexture`,
  `ConvertNColorsTexture`). Reusar esse decoder evita reimplementar formatos.

Referência de UX: a aba **3D/RE do No$gba** lista o stream do GXFIFO decodificado
(`begin_vtxs`, `mtx_restore`, `texcoord`, `vtx`, `end_vtxs`, …) com parâmetros e
resultados de vértice (`screenpos x/y/z/w`) e atributos (difusa/ambiente/emissão/
especular, light mask, shininess). É o alvo de leitura; não é preciso replicar a UI.

## Goals / Non-Goals

**Goals:**

- Ler o estado 3D decodificado sob demanda, sem reimplementar o pipeline.
- Dumpar os polígonos do frame renderizado (atributos + vértices).
- Dumpar as **texturas usadas no frame** (metadados + decode para RGBA), como no
  viewer de textura do No$gba.
- Observar a ordem/profundidade da fila GXFIFO com `cmd`, `param`, `pc`, `frame`.
- Tools MCP finas sobre o canal; testes com canal fake.
- Custo zero por quadro quando nada está ligado.

**Non-Goals:**

- Reimplementar rasterização/transformação no MCP.
- Editar/poke de textura (change posterior).
- Streaming contínuo por quadro (eventfd) — a trace é poll-based.
- Replicar a UI do No$gba; só o stream/estado decodificado importa.

## Decisions

- **Hook no `WriteToGXFIFO`, não no `CmdFIFOWrite`.** `CmdFIFOWrite` também é
  chamado no refill interno da `CmdStallQueue` (durante o processamento), o que
  poluiria a ordem com o PC do leitor. `WriteToGXFIFO` é o caminho de quem
  enfileira (CPU/DMA), que é a pergunta de debug. Alternativa descartada:
  instrumentar `CmdFIFO` genérico (perde a noção de autor).
- **`pc` é o PC da CPU no enfileiramento.** Para FIFO alimentado por DMA, o PC pode
  ser o da CPU no momento e não o programador do DMA; documentar e usar
  `dma_trace` quando a distinção importar. Alternativa descartada: correlacionar
  com o DMA programador neste change (mais estado, mais acoplamento).
- **Ring SPSC (produtor EmuThread, consumidor cliente) + `start/read/stop`.** O
  hook é O(1) e sem alocação; usar um ring single-producer/single-consumer com
  índices atômicos para **não pagar mutex por entrada** no caminho quente. Reusar
  o formato do `TraceRing` (drops o mais antigo + `dropped`) por baixo. Se ficar
  com `TraceRing`+mutex, medir (ver Performance). Alternativa descartada: eventfd
  por cliente como o `dma.trace` — desnecessário para inspeção por janela.
- **Decode no `read` (thread do cliente), não no hook.** O hook grava só o cru
  (`cmd`, `param`, `pc`, `frame`, `fifo`); `3d.gxfifo.read` acumula parâmetros por
  comando e resolve o nome (tabela `CmdNumParams` + nomes canônicos, ex.:
  `begin_vtxs`, `mtx_restore`, `texcoord`, `vtx`, `end_vtxs`, `begin/end` de
  display list). Isso mantém a EmuThread O(1) e sem alocação/JSON. Alternativa
  descartada: decodificar no hook (viola a regra de performance).
- **Resultados de vértice vêm de `3d.polygons`.** No melonDS, `FinalPosition`
  (screenpos) só é calculado no transform de viewport, quando o polígono é
  submetido — não no comando `vtx`. Então o trace mostra o stream e os parâmetros
  (coordenadas de entrada, matriz/modo, texcoord), e a **posição final de tela por
  vértice** fica em `3d.polygons`. É essa posição que serve para localizar um
  elemento e depois reposicioná-lo. Alternativa descartada: capturar screenpos no
  trace no enfileiramento (indisponível nesse ponto).

  Reposicionar um elemento é um passo **posterior de escrita** (patch/poke do
  input: coordenadas, matriz ou template), fora deste change.
- **Snapshot no VBlank/fim de frame, one-shot.** Estado/polígonos/texturas
  observam o **frame completo**: o pedido arma uma flag e, no próximo
  `GPU3D::VBlank` (depois de finalizar `RenderPolygonRAM` e antes de trocar o
  banco), copia-se um snapshot consistente e devolve. Evita ler o frame pela
  metade (frame × lista divergentes) e mantém custo zero sem pedido. Alternativa
  descartada: pausar em qualquer ponto e ler os campos (risco de frame parcial).
- **Decode de textura reusa `GPU3D_Texcache`.** `3d.textures` enumera os pares
  únicos `(TexParam, TexPalette)` dos polígonos do frame e decodifica com as
  funções `Convert*` (bitmap/compressed/AXIY/Ncolors) para RGBA; `3d.texture`
  serve o frame binário. Não reimplementar formatos nem wrapping.
  Alternativa descartada: `TextureLookup` por texel (lento e duplicaria o
  wrapping).
- **Polígonos de `RenderPolygonRAM`.** É a lista efetivamente renderizada do frame
  (não o banco em construção). Limite `max_items` (1..8192) e `vertices` opcional.
- **Windows:** métodos viram stubs, como `dma.trace`.

## Performance

- **Sem nada ligado:** 1 branch (`OnGXCommand` nulo) por palavra de GXFIFO; sem
  snapshot e sem custo por quadro. Praticamente indistinguível.
- **Trace ligada:** custo por entrada ≈ push de 20 B + sincronização. Mutex
  não-contencioso ≈ 50 ns/entrada → 10k entradas/frame ≈ 0,5 ms (~3% de 16,7 ms);
  100k ≈ 5 ms (inaceitável). Por isso o ring é **SPSC lock-free**; se ficar com
  mutex, medir e impor limite/amostragem. Decode + JSON só no `read` (thread do
  cliente), nunca na EmuThread.
- **Snapshot no VBlank:** one-shot sob pedido; cópia limitada a
  `RenderNumPolygons` (≤2048) + vértices (≤10/polígono) — ordem de 1–2 MB no pior
  caso, tipicamente muito menos; só quando pedido, nunca por quadro.
- **Textura:** decode sob pedido; até 256×256 RGBA (~256 KB) por textura; nunca
  por quadro.
- **Memória:** ring default 65536 × 20 B ≈ 1,25 MiB; snapshot e textura
  decodificada são bounded e liberados após a leitura.
- **UI/viewer:** refresh limitado (ver `add-3d-viewer`); congelado, só repaint do
  snapshot, sem tocar a EmuThread.

## Risks / Trade-offs

- [Corrida ao ler estado/counts] → snapshot one-shot no VBlank, não leitura
  concorrente.
- [Frame × lista de polígonos divergentes] → resolvido por design: o snapshot é
  tirado no VBlank, quando `RenderPolygonRAM` já está finalizado.
- [Ponteiros de vértice inválidos entre frames] → o snapshot copia os dados no
  VBlank; não se drena ponteiro vivo depois.
- [Formato/VRAM de textura] → reusar o decoder do renderer e validar contra o
  No$gba; formatos não suportados viram erro/aviso claro.
- [Trace enche em loop] → ring fixo + `dropped`; o agente lê/limpa (`start`
  reinicia).
- [Cena 3D densa + trace] → se o ring não for SPSC, o custo por entrada pode
  pesar; medir frame time ligado/desligado e manter SPSC/limite.
- [PC ambíguo em FIFO alimentado por DMA] → documentado; parear com `dma_trace`.
- [Custo no enfileiramento] → uma chamada de função por entrada, somente com hook
  armado; sem `OnGXCommand`, um `if` por entrada.

## Migration Plan

Aditivo. Sem a trace ligada, o único custo novo no núcleo é a checagem de ponteiro
no enfileiramento. Tools novas não alteram as existentes. Atualizar skill e
validar com `openspec validate --strict`, build do fork, `pytest`/`pyright`/
`lint-imports` e smoke real numa cena 3D do KH.

## Open Questions

- Texturas animadas/múltiplas no mesmo frame: enumerar por par
  `(TexParam,TexPalette)` basta? Validar numa cena do KH.
- Incluir `screenpos`/atributos finais no trace exigiria um hook de execução;
  por ora ficam em `3d.polygons`.
- Um `3d.gxfifo.state` para ver a fila **no momento** (não histórico)? Avaliar
  depois do trace.
