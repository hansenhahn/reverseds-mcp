## 1. Emulador — snapshot no VBlank

- [ ] 1.1 Adicionar um pedido one-shot de snapshot (flag + mutex) consumido em
  `GPU3D::VBlank()`, após finalizar/ordenar `RenderPolygonRAM` e antes de trocar
  `CurRAMBank`: copiar estado + polígonos (e índices de textura) para um buffer
  consistente do frame. Verificar: com o pedido armado, o snapshot reflete o frame
  completo; sem pedido, custo zero por quadro.

## 2. Emulador — estado 3D

- [ ] 2.1 Adicionar `3d.state` ao `ControlServer` devolvendo o snapshot do VBlank
  (`DispCnt`, `GXStat`, níveis de `CmdFIFO`/`CmdPIPE`/`CmdStallQueue`,
  `MatrixMode`, matrizes projeção/posição/vetor/textura/clip, `Viewport`, alpha,
  fog, toon/edge, contadores). Verificar: chamada manual devolve JSON coerente com
  um frame congelado e não lê campos vivos fora do snapshot.

## 3. Emulador — polígonos

- [ ] 3.1 Adicionar `3d.polygons` (params `max_items`, `vertices`) sobre o
  snapshot do VBlank: atributos e, quando pedido, vértices (`FinalPosition`,
  `FinalZ/W`, cor, texcoord). Verificar: numa cena 3D, `count == min(total,
  max_items)` e os vértices ficam dentro do frame.

## 4. Emulador — texturas

- [ ] 4.1 Adicionar `3d.textures` enumerando os pares únicos
  `(TexParam, TexPalette)` dos polígonos do snapshot, com formato/tamanho/paleta/
  endereço de VRAM. Verificar: a lista casa com os polígonos do frame.
- [ ] 4.2 Adicionar `3d.texture` que decodifica uma textura para RGBA reusando
  `GPU3D_Texcache` (`ConvertBitmapTexture`/`ConvertCompressedTexture`/
  `ConvertAXIYTexture`/`ConvertNColorsTexture`), servindo o frame binário.
  Verificar: uma textura conhecida (ex.: fonte/UI) bate com o No$gba/visual.
- [ ] 4.3 MCP: `gpu3d_textures` e `gpu3d_texture_dump` (salva PNG em `/out`,
  como `screen_capture`). Verificar: PNG gerado e abrível; metadados coerentes.

## 5. Emulador — trace GXFIFO

- [ ] 5.1 Adicionar `NDS::OnGXCommand(cmd, param, pc, frame, fifo)` e chamá-lo em
  `GPU3D::WriteToGXFIFO` (antes de `CmdFIFOWrite`), usando `NDS.ARM9->R[15]` e
  `NDS.NumFrames`. Verificar: com hook nulo, build e emulação sem regressão.
- [ ] 5.2 Adicionar `GXEvent` + `TraceRing` + mutex + `gxActive` ao
  `ControlServer` e os métodos `3d.gxfifo.start/read/stop`, com `read` drenando
  `{count, dropped, commands[]}` cru e `stop` mantendo o buffer legível.
  Verificar: start → rodar N frames → read devolve ordem/profundidade; stop →
  read ainda devolve o que sobrou; sem start, `count=0`.
- [ ] 5.3 Decodificar no `read` (thread do cliente): acumular parâmetros por
  comando e resolver o nome por uma tabela (comprimento de `CmdNumParams` + nomes
  canônicos: `begin_vtxs`, `mtx_restore`, `texcoord`, `vtx`, `end_vtxs`, etc.),
  devolvendo `name` + `params` além dos campos crus. Verificar: numa cena 3D do
  KH, a leitura mostra o stream no estilo No$gba (sequência `begin_vtxs` … `vtx` …
  `end_vtxs`) coerente com `3d.polygons`.
- [ ] 5.4 Stubs Windows para os métodos novos. Verificar: build no caminho `_WIN32`.

## 6. MCP

- [ ] 6.1 Criar `tools/three_d.py` com `gpu3d_state`, `gpu3d_polygons`,
  `gpu3d_textures`, `gpu3d_texture_dump`, `gxfifo_trace_start`,
  `gxfifo_trace_read(seconds)` e `gxfifo_trace_stop`, registrando em
  `tools/server.py` e repassando os comandos já decodificados. Verificar:
  `list_tools` mostra as sete tools; testes com canal fake cobrem sucesso e erro.
- [ ] 6.2 Documentar no docstring o cuidado do `pc` em FIFO alimentado por DMA e o
  fluxo `start → esperar → read → stop`. Verificar: docstring e teste do fluxo.

## 7. Documentação

- [ ] 7.1 Atualizar a skill (`references/concepts.md` e `references/display.md`)
  com as tools 3D, indicando que `render_layer(3d)` continua sendo o oracle da
  imagem, que a trace mostra a **ordem de enfileiramento** e que o snapshot é do
  **frame completo (VBlank)**. Verificar: inventário de tools inclui as novas e o
  fluxo está descrito.

## 8. Validação

- [ ] 8.1 Emulador: build `Release` (JIT off, GDB on) sem regressão. Verificar:
  `cmake --build build -j` conclui.
- [ ] 8.2 MCP: `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports`
  verdes. Verificar: saída sem erros.
- [ ] 8.3 `openspec validate add-3d-inspection --strict` verde.
- [ ] 8.4 Smoke real numa cena 3D (KH): `gpu3d_state`/`gpu3d_polygons` coerentes
  com o frame; `gpu3d_textures`/`gpu3d_texture_dump` batem com o No$gba;
  `gxfifo_trace_*` mostra ordem/profundidade com `pc/frame`. Verificar: valores
  coerentes com `render_layer(engine=A, layer=3d)` no mesmo frame.
- [ ] 8.5 Medir performance numa cena densa: frame time com trace desligada
  (esperado ≈ sem mudança), com trace ligada (custo aceitável; senão SPSC/limite)
  e freeze (snapshot one-shot). Verificar: números antes/depois registrados.
