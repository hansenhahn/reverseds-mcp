## Context

Ver `proposal.md`. `BgLayer` já resolve `map_size`, `char_base`, `screen_base`, `bpp`,
scroll (C2) e células text/affine. `DisplayReader` lê tiles e células. Falta varrer o mapa
inteiro e compor a imagem; `render_layer` só cobre a janela visível.

## Goals / Non-Goals

**Goals:**
- Dump do mapa virtual inteiro (text/affine) em JSON.
- Composição do mapa inteiro em PNG (4/8bpp, flips, paleta BG).
- Leituras bulk (mapa/tiles/paleta) para não fazer uma chamada gdb por célula/tile.
- Reusar `BgLayer`/`cell()`/`decode()`; sem emulador.

**Non-Goals:**
- Aplicar mosaic/alpha/window/rotation (é um dump do mapa, não um screenshot).
- Extended palettes/bitmap/3D (erro claro).
- Renderizar o map via renderer do emulador (fica como follow-up se affine/efeitos exigirem).

## Decisions

### 1. Dump

`dump_tilemap(engine, bg)`:

1. Monta `BgLayer` com scroll (C2).
2. Lê `screen_base` em bulk: `entries = (w/8)*(h/8)`, `bytes = entries * (2 text | 1 affine)`.
3. Para cada célula, usa `layer.cell(cx*8, cy*8)` e `entry = map_bytes[entry_addr - screen_base]`.
4. `layer.decode(info, entry)` → tile/paleta/flips.
5. Grava JSON em `bgmap_<engine>_<bg>.json` via `FileStore`; retorna
   `{path, width, height, cell_count, kind, bpp, screen_base, char_base}`.

O JSON inclui `cells: [{cx,cy,entry,tile_index,tile_addr,palette,flip_h,flip_v}]`.

### 2. Composição

`render_bg_map(engine, bg)`:

- Mesmo dump; lê `char_base` em bulk até `(max_tile+1)*tile_size` e a paleta BG em 512 B.
- Decodifica tile 8×8 (`tile_indices(data,bpp)`), aplica flips e compõe RGBA.
- Pixel 0 = transparente (alpha 0); text 4bpp usa `entry.palette*16 + pixel`; 8bpp/affine
  usa `pixel`.
- BGR555→RGB: `(v & 0x1F)<<3`, `((v>>5)&0x1F)<<3`, `((v>>10)&0x1F)<<3` (com replicação dos
  bits altos).
- Salva `bgmap_<engine>_<bg>.png`; retorna metadados.

### 3. Paleta

`BgLayer.palette_base`: engine A `0x05000000`, B `0x05000400` (BG). Lê 512 B (256 cores) por
composição. Extended palettes ficam fora do MVP.

### 4. Bulk reads

- Mapa: 1 leitura (`screen_base`, `entries*size`).
- Tiles: 1 leitura (`char_base`, `(max_tile+1)*size`, cap 1024 tiles).
- Paleta: 1 leitura (512 B).
Total ~3 leituras por mapa, independente do número de células.

### 5. Erros

- `kind` fora de `text`/`affine` → erro com hint.
- Mapa/tiles fora da VRAM/ilegíveis → erro do debugger propagado.
- `bg` inválido → erro.

## Risks / Trade-offs

- [Affine é dump plano] → o mapa é renderizado sem a transformação de tela; é um dump de
  dados, não o screenshot. Documentar.
- [Mosaic/alpha/window] → não aplicados; para o visual exato, usar `render_layer`.
- [Tiles grandes] → leitura até o maior tile usado; cap em 1024; VRAM pode ser menor.
- [Paleta write-only] → paleta é legível pela CPU (`0x050...`), sem shadow.
- [Artefatos grandes] → JSON/PNG vão para `/out`; a tool devolve caminho, não o conteúdo.

## Migration Plan

Aditivo. Atualizar `mcp-re-workflows` e testes. `pytest`, `pyright`, `lint-imports`,
`openspec validate --strict`; smoke no menu de status e num BG 512×512.

## Open Questions

- Renderer do emulador para affine/efeitos (C3b)? (Follow-up.)
- Exportar tile sheet junto do mapa? (Opcional.)
- Limite de células para retorno inline vs sempre arquivo? (Proposta: sempre arquivo.)
