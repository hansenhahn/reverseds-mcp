## Context

Ver `proposal.md`. `BgLayer.cell(x,y)` já resolve a célula em coordenadas **do mapa**;
`render_layer` desenha a camada via renderer. C1 adicionou `BGxHOFS/VOFS` ao schema, mas
`VideoState`/`BgLayer` ainda não leem esses valores. O objetivo é ligar a tela (256×192 do
engine) ao mapa/célula/tile.

## Goals / Non-Goals

**Goals:**
- Expor scroll por BG no `video_state`.
- Resolver pixel da tela → célula/tile para BG text, com wrap.
- Destacar a célula no PNG do `render_layer`.
- Manter `map_cell` (coordenadas de mapa) compatível.

**Non-Goals:**
- Affine/rotation/scale no MVP (erro claro; follow-up).
- Obj/3D no destaque (só BG text).
- Renderizar o mapa virtual inteiro (isso é C3).

## Decisions

### 1. Scroll no `VideoState`

`VideoState` ganha `scrolls: tuple[tuple[DecodedRegister, DecodedRegister], ...]` com
`(BGxHOFS, BGxVOFS)` para BG0-3. `VideoReader.state` lê `base+0x10+4*i`/`base+0x12+4*i`
via schema (C1). `video_state` inclui `scroll: [{hofs, vofs}, ...]` por BG.

### 2. `BgLayer.cell_from_screen`

`BgLayer` ganha `hofs`/`vofs` (default 0) e:

```text
map_x = (screen_x + hofs) mod map_width
map_y = (screen_y + vofs) mod map_height
cell = cell(map_x, map_y)
```

- Só `kind == "text"`; affine/extended/3d → `ValueError` com hint.
- `screen_x`/`screen_y` em coordenadas do engine (0..255, 0..191).
- Retorna `ScreenCell` com `cell`, `map_x/map_y`, `screen_cell`, `screen_rect`.

**Alternativa:** colocar scroll no `BgCellInfo`; descartado para manter o domínio de célula
independente do tempo/scroll.

### 3. Tool `cell_at_screen`

`cell_at_screen(engine, bg, x, y)` valida 0..255/0..191, usa `DisplayReader.cell_at_screen` e
serializa o `BgCell` + `screen_rect` + scroll. Reaproveita `_cell_dict` existente.

### 4. `render_layer(..., highlight=[x,y])`

- Só para `layer=bg0..bg3` (não obj/3d).
- Exige debugger conectado (precisa ler scroll/mapa); sem gdb → erro + hint.
- Renderiza normalmente, salva os PNGs e desenha um retângulo 8×8 na tela do engine
  (`video_state(engine).screen`). Se `screens` não incluir essa tela → erro + hint.
- Retorna `{"paths", "screen", "cell"}`.

A seleção do PNG usa a ordem top/bottom do `save_framebuffer_pngs`; o desenho é feito com
Pillow depois do save.

### 5. Sem emulador

Tudo usa o schema C1 + debugger + renderer existentes. Nenhuma mudança no fork.

## Risks / Trade-offs

- [Scroll write-only lê 0] → se o melonDS não expuser o valor real, a correlação fica
  deslocada; o resultado inclui `hofs/vofs` para o agente detectar (e `raw=` pode decodificar
  um valor conhecido).
- [Wrap na borda] → a célula pode aparecer partida; o MVP destaca o `screen_rect` do pixel
  consultado, não a célula inteira.
- [Affine] → erro claro no MVP; C2b pode adicionar matriz affine.
- [Destaque em `screens=both`] → escolher o índice pela tela do engine; se ausente, erro.
- [Cliente antigo] → `render_layer` sem `highlight` continua idêntico.

## Migration Plan

Aditivo. Atualizar `mcp-video-tools` e testes. `pytest`, `pyright`, `lint-imports`,
`openspec validate --strict`; smoke no menu de status (célula conhecida, com e sem scroll).

## Open Questions

- Incluir affine/rotation em C2b ou deixar para C3? (MVP: text only.)
- Destacar a célula inteira ou só o pixel consultado? (MVP: 8×8 do pixel.)
- Expor `screen_rect` em coordenadas top/bottom absolutas? (MVP: engine-local.)
