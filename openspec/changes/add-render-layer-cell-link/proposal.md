## Why

`render_layer` mostra uma camada, e `map_cell(engine, bg, x, y)` resolve uma célula — mas em
**coordenadas do mapa**, não da tela. Hoje o agente precisa correlacionar manualmente scroll,
célula e tile para responder “o que é este pixel/célula na tela?”. C1 passou a decodificar
`BGxHOFS/VOFS`, então essa correlação pode ser feita pelo MCP.

## What Changes

- `video_state` passa a expor o scroll (`BGxHOFS/VOFS`) por BG (engine A/B).
- `BgLayer` ganha `hofs`/`vofs` e `cell_from_screen(screen_x, screen_y)` para BG **text**:
  converte pixel da tela → pixel do mapa (com wrap) → célula/tile.
- Nova tool `cell_at_screen(engine, bg, x, y)` devolve a célula, o tile/endereço, o
  `screen_rect` e o scroll usado.
- `render_layer(..., highlight=[x, y])` desenha um retângulo 8×8 na célula indicada (PNG da
  tela do engine) e devolve os metadados da célula.
- Affine/rotation fica fora do MVP: `cell_from_screen` retorna erro claro para affine.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-video-tools`: correlação tela→célula e destaque no `render_layer`.

## Impact

- MCP: `application/video.py` (scroll no `VideoState`), `domain/display.py`
  (`BgLayer`/`ScreenCell`), `application/display.py`, `tools/video.py`, `tools/re.py`, testes.
- Emulador: **nenhuma mudança**.
