## Why

Fechar o caminho **display → tile → VRAM/RAM → DMA** ainda exige várias chamadas manuais
(`video_state`, `read_vram`, `dma_trace_*`, busca de padrão em RAM). Isso é o elo que falta
entre “o que está na tela” e “qual buffer/código gerou”.

## What Changes

- **`map_cell(engine, bg, x, y)`**: resolve a célula do BG (text ou affine) para entrada do
  mapa, índice do tile, endereço do tile, paleta/flip/bpp, char/screen base e tamanho do mapa.
- **`vram_tile_bytes(engine, tile_index, layer, bg, bpp)`**: lê os bytes de um tile BG/OBJ
  (4/8bpp) direto da VRAM.
- **`find_tile_in_ram(engine, tile_index, ..., ram_addr, ram_size)`**: busca o padrão do tile
  na RAM principal (até 4 MiB) e devolve os endereços encontrados.
- **`dma_source(vram_addr, seconds, ...)`**: roda o trace de DMA por uma janela e devolve os
  transfers cujo **destino** cobre o endereço de VRAM, com `src/dst/len/cpu/pc` e símbolo.
- Sem mudança no emulador.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-re-workflows`: adiciona helpers display↔RAM e correlação DMA.

## Impact

- MCP: `domain/display.py` (novo), `application/display.py` (novo),
  `application/dma_trace.py` (`find_destination`), `tools/re.py`, testes.
- Emulador: **nenhuma mudança**.
