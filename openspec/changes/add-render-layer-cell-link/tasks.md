## 1. Domínio

- [x] 1.1 `BgLayer` ganha `hofs`/`vofs` e `cell_from_screen(screen_x, screen_y)` com wrap;
  adicionar `ScreenCell` (`cell`, `map_x/y`, `screen_cell`, `screen_rect`).
  Verificar: scroll 0 e scroll ≠0 resolvem a célula esperada; affine retorna erro.
- [x] 1.2 Testes de wrap (256/512) e de célula na borda.

## 2. Leitura/estado

- [x] 2.1 `VideoState`/`VideoReader` leem `BGxHOFS/VOFS` (A/B) via schema; `video_state`
  inclui `scroll` por BG. Verificar: fake debugger com scroll conhecido.
- [x] 2.2 `DisplayReader.cell_at_screen` e `_bg_layer` usam o scroll do estado.
  Verificar: célula de tela com scroll resolve o `entry_addr` correto.

## 3. Tools

- [x] 3.1 `cell_at_screen(engine, bg, x, y)` (0..255/0..191) devolve célula + tile +
  `screen_rect` + scroll. Verificar: teste de serialização e coordenada inválida.
- [x] 3.2 `render_layer(..., highlight=[x,y])`: só bg0-3, exige gdb, desenha 8×8 na tela do
  engine e devolve `cell`/`screen`. Verificar: teste do desenho/seleção de PNG com fake.
- [x] 3.3 Affine/obj/3d retornam erro claro com hint.

## 4. Validação

- [x] 4.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-render-layer-cell-link --strict`.
- [x] 4.2 Smoke real no menu de status: `cell_at_screen` com scroll 0 e com scroll forçado;
  `render_layer(highlight=...)` gera PNG com o retângulo na célula esperada.

### Smoke real (2026-11-02)

- Engine B (BG0, `screen=bottom`): `cell_at_screen` → `map=[0,0]`, `tile=0`, `tile_addr=0x06208000`.
- `render_layer(B, bg0, bottom, highlight=[0,0])` gerou PNG com pixel `(0,0)` vermelho e
  devolveu `cell`/`screen`.
- Engine A (BG1, `screen=top`): mesmo fluxo validado.
