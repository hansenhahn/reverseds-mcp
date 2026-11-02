## Context

Ver `proposal.md`. `DmaTrace.collect(seconds)` lê `event.dma` e devolve a lista decodificada;
`tools/control.py` serializa tudo. O trace já tem `cpu`, `channel`, `source`, `destination`,
`length`, `pc` e controle decodificado.

## Goals / Non-Goals

**Goals:**
- Reduzir o payload por chamada com filtros e `summary`.
- Permitir “só VRAM”, “só ARM9”, “só canal 1”, “só len ≥ N”.
- Não mudar o emulador nem o formato do `event.dma`.

**Non-Goals:**
- Filtrar no emulador (pode ser follow-up se o custo de coleta importar).
- Mudar o ring/batching do canal.
- Reordenar/filtrar por tempo além da janela `seconds`.

## Decisions

### 1. Filtro no MCP, durante a coleta

`collect(seconds, *, dst_range, src_range, cpu, channel, min_len, max_items)` filtra cada
`DmaTransfer` antes de acumular. Ranges são `[start, end)` e comparam o endereço do lado
correspondente (`destination.address`/`source.address`). `cpu` é 0=ARM9/1=ARM7 no serviço;
a tool aceita `"arm9"`/`"arm7"`. `channel` é 0..3. `min_len` em bytes.

`max_items` limita os transfers **retornados**; ao atingir o limite, a coleta para (evita
acumular/Serializar o resto). `None` = sem limite.

**Alternativa:** filtrar no emulador (`dma.trace.start` com filtros). Descartado agora para
não exigir rebuild; o filtro no MCP já resolve o payload.

### 2. `summary` agrega por `(src,dst,len,cpu,channel,pc)`

Quando `summary=true`, a tool devolve `groups` com `source`, `destination`, `length`, `cpu`,
`channel`, `pc`, `pc_symbol` e `count`, ordenados por `count` desc. `count` total de transfers
filtrados também é exposto. Sem `summary`, devolve `transfers` como hoje.

### 3. Validação de parâmetros

Ranges com exatamente dois inteiros, `start <= end`; `cpu` inválido, `channel` fora de 0..3,
`min_len < 0` e `max_items <= 0` retornam `error` + `hint`. `max_items` é opcional.

## Risks / Trade-offs

- [Filtro só no MCP ainda coleta áudio] → `max_items`/`seconds` limitam; filtro no emulador
  fica como follow-up se necessário.
- [Ranges inclusivos/exclusivos] → documentar `[start, end)`.
- [Summary esconde detalhes] → `summary=false` continua disponível.
- [CPU como string] → tool traduz `"arm9"/"arm7"`; o serviço usa 0/1.

## Migration Plan

Aditivo: parâmetros novos com defaults preservam `dma_trace_read(seconds)`. Validar com
`pytest`, `pyright`, `lint-imports`, `openspec validate --strict` e smoke real.

## Open Questions

- Filtrar no emulador (`dma.trace.start` com `dst_range`) para reduzir I/O? (Follow-up.)
- Expor `dropped`/`overflow` do ring na leitura? (Pode entrar junto.)
