## 1. Emulador — histórico de origem de escrita

- [x] 1.1 Adicionar ao `ControlServer` um ring bounded de writes de origem
  (`dst_lo`, `dst_hi`, `src`, `len`, `pc`, `frame`, `kind`) com
  `origin.start`/`origin.stop`/`origin.query` (armado sob demanda, O(1) por
  transferência, drops contados). Alimentar a partir de `NDS.OnDmaTransfer`.
  Verificar: sem `start`, custo zero; com `start`, uma transferência para VRAM
  aparece na consulta com `src`/`pc`/`frame`.
- [x] 1.2 Consulta por sobreposição de faixa (`addr`, `len`, `max_age_frames`,
  `max_hits`), mais recente primeiro; nada casando → `unknown` com dica.
  Verificar: faixa sem write retorna `unknown`; múltiplas transferências voltam
  ordenadas.
- [x] 1.3 Origem do GXFIFO/display list: registrar no histórico as transferências
  cujo destino cobre `0x04000400` e expor `gxfifo.origin` com `src`/`pc`/`frame`.
  Verificar: um DMA de display list é encontrado, e um buffer dumpado bate com o
  stream observado.

## 2. MCP — origem da textura e do display list

- [x] 2.1 `gpu3d_texture_source(index|tex_param, tex_palette, ...)`: ler os bytes
  crus via `3d.texture_raw`, buscar o mesmo padrão na RAM e devolver os buffers
  candidatos (`candidates`, `count`, `digest`, `unknown`).
  Verificar: numa cena do KH, acha pelo menos um buffer cujo conteúdo bate com a
  textura (ou `unknown=true` honesto).
- [x] 2.2 Opção `dump_source=true`: ler o(s) buffer(s) candidato(s) (chunked) e
  salvar `.bin` em `/out`. Verificar: bytes do candidato batem com a textura crua.
- [x] 2.3 `gxfifo_source(...)`: devolve o `src`/`pc`/`frame` do display list
  (histórico de origem) e, opcionalmente, dump do buffer. Verificar: buffer casa
  com os comandos do trace.
- [x] 2.4 Erros claros: `unknown` com hint quando não há candidato/histórico.

## 3. MCP — decode tipado do GXFIFO

- [x] 3.1 `gxfifo_trace_read(decode="typed")`: decodificar parâmetros por comando
  (`vtx_16`/`vtx_10`/`vtx_xy`/`vtx_xz`/`vtx_yz`/`vtx_diff` → x/y/z;
  `texcoord` → u/v; `mtx_*` → modo/elementos; `begin_vtxs` → primitiva).
  Verificar: uma sequência `begin_vtxs`…`vtx`…`end_vtxs` reconstruída bate com os
  vértices/polígonos observados.
- [x] 3.2 Manter o formato cru como default e documentar quando usar o tipado.

## 4. MCP — busca de buffer na RAM

- [x] 4.1 `find_bytes_in_ram(hex | from_addr/size, ram_start, ram_size, max_hits)`:
  busca em blocos, com cap; devolve endereços. Verificar: um padrão extraído de
  VRAM é encontrado no buffer de RAM de origem.

## 5. Documentação

- [x] 5.1 Atualizar a skill (global → repo) com "origem de asset 3D": fluxo
  VRAM → write → RAM → loader, e que extração/importação é externa
  (`kheartsds-tool`).
- [x] 5.2 Deixar explícito o escopo: para no decomp; sem formatos prontos.

## 6. Validação

- [x] 6.1 Emulador: build `Release` (JIT off, GDB on) `-j1` sem regressão.
- [x] 6.2 MCP: `pytest`, `pyright`, `lint-imports` verdes.
- [x] 6.3 `openspec validate add-3d-asset-re --strict` verde.
- [ ] 6.4 Smoke real no KH: recarregar uma cena com o histórico armado, achar a
  origem de uma textura (src/pc/frame) e do display list; dump do buffer de origem
  coerente com VRAM/GXFIFO.
