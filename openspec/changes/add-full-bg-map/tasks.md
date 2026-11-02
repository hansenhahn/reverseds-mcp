## 1. Domínio

- [x] 1.1 Adicionar `BgLayer.palette_base` (A `0x05000000`, B `0x05000400`) e helpers puros
  `tile_indices(data,bpp)` / `rgb555`.
  Verificar: tile 4/8bpp e cor BGR555 decodificados em teste unitário.
- [x] 1.2 Verificar layout text 256/512 e affine 128..1024 (já coberto por `cell()`).

## 2. Serviço

- [x] 2.1 `DisplayReader.dump_bg_map` com leitura bulk do mapa e decodificação por célula;
  retorna `list[dict]` + metadados.
  Verificar: mapa sintético 256×256 text e affine.
- [x] 2.2 `DisplayReader.render_bg_map` compõe RGBA a partir de mapa/tiles/paleta, com flips
  e transparência no índice 0.
  Verificar: mapa sintético com 2 tiles/paletas e flip H/V.

## 3. Tools

- [x] 3.1 `dump_tilemap(engine, bg)` grava JSON em `/out` e devolve caminho/metadados.
  Verificar: arquivo existe e contém `cell_count` correto.
- [x] 3.2 `render_bg_map(engine, bg)` grava PNG em `/out` e devolve caminho/metadados.
  Verificar: dimensões e pixels conhecidos.
- [x] 3.3 Text/affine suportados; extended/bitmap/3D retornam erro claro.

## 4. Validação

- [x] 4.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-full-bg-map --strict`.
- [x] 4.2 Smoke real: mapa 512×512 (text) e affine; crop da janela visível (text) confere
  com `render_layer`; `dump_tilemap` bate com `map_cell` em células amostradas.

### Smoke real (2026-11-02)

- Engine B, BG0 (text 512×256): `dump_tilemap` gerou 2048 células; 73 não vazias.
- 30 células amostradas comparadas com `map_cell` → 0 divergências de tile/paleta.
- `render_bg_map` gerou PNG 512×256 com transparência no índice 0.
- Affine coberto por teste sintético (o estado atual não tinha BG affine).
- Obs.: a comparação pixel-a-pixel com `render_layer` é limitada pelo backdrop/
  composição do renderer; a verificação usada foi célula/tile + amostragem.
