## 1. Display→tile

- [x] 1.1 Criar `domain/display.py` (bg_kind, map size, char/screen base, cell entry,
  decode text/affine, obj_tile_address) e `application/display.py` (map_cell, tile_bytes,
  find_tile_in_ram). Verificar: testes de domínio e serviço com fake memory.
- [x] 1.2 Tools `map_cell`, `vram_tile_bytes` e `find_tile_in_ram` em `tools/re.py`.
  Verificar: testes de tool e descoberta.

## 2. DMA source

- [x] 2.1 Adicionar `DmaTrace.find_destination` (start/collect/stop + filtro de faixa) e a
  tool `dma_source`. Verificar: teste com fake trace.

## 3. Validação

- [x] 3.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-display-ram-helpers --strict` verdes (163 testes).
- [ ] 3.2 Smoke real opcional: mapear uma célula do menu, achar o tile na RAM e um DMA do
  atlas por `dma_source`.
