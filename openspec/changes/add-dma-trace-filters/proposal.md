## Why

`dma_trace_read(seconds)` devolve **todos** os transfers do período. Na sessão real isso
gerou ~29k transfers e ~15 MB de JSON, quase tudo áudio (`0x021A3C10 -> 0x07000400`), e a
chamada foi truncada. Filtrar/agregar no MCP resolve o problema sem tocar no emulador.

## What Changes

- `dma_trace_read` ganha filtros: `dst_range`, `src_range`, `cpu`, `channel`, `min_len`,
  `max_items` e `summary`.
- `summary=true` agrega por `(src, dst, len, cpu, channel, pc)` e devolve grupos com
  contagem, em vez da lista crua.
- Filtro/agregação no MCP (`application/dma_trace.py`), sem mudança no emulador.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-control-tools`: trace de DMA filtrável/resumível.

## Impact

- MCP: `application/dma_trace.py`, `tools/control.py`, testes.
- Emulador: **nenhuma mudança**.
