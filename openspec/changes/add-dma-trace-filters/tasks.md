## 1. Serviço

- [x] 1.1 `DmaTrace.collect` aceita `dst_range`, `src_range`, `cpu`, `channel`, `min_len`
  e `max_items`, filtrando durante a coleta; ranges `[start, end)`.
  Verificar: teste com transfers mistos (VRAM/áudio, CPU/canal) e `max_items`.
- [x] 1.2 `DmaTrace.summarize` agrega por `(src,dst,len,cpu,channel,pc)` com `count`,
  ordenado por contagem desc. Verificar: dois transfers iguais → um grupo com count 2.

## 2. Tool

- [x] 2.1 `dma_trace_read(..., dst_range, src_range, cpu, channel, min_len, summary,
  max_items)`: valida parâmetros, traduz `"arm9"/"arm7"` e devolve `transfers` ou `groups`.
  Verificar: testes de filtro, summary, validação e compatibilidade sem argumentos.
- [x] 2.2 Atualizar docstring e a skill. Verificar: docs citam `dst_range`/`summary`.

## 3. Validação

- [x] 3.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-dma-trace-filters --strict`.
- [x] 3.2 Smoke real: `dma_trace_read` com `dst_range` de VRAM e `summary=true` em uma
  janela com áudio; conferir que o payload não traz áudio.

### Smoke real (2026-11-02)

- `savestate_3` + `dst_range` de VRAM → só transfers para `0x0600...`/`0x0620...`.
- `cpu="arm9"`, `min_len=6000`, `summary=true`, `max_items=3` → grupo de áudio
  (`0x04000400`) com `count=3`, sem a lista crua.
- `summary` agrupou corretamente os transfers repetidos por `(src,dst,len,cpu,ch,pc)`.
