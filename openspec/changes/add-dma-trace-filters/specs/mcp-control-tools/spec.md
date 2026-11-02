## ADDED Requirements

### Requirement: DMA trace filtrável

`dma_trace_read` SHALL aceitar filtros `dst_range`, `src_range`, `cpu` (`arm9`/`arm7`),
`channel`, `min_len`, `max_items` e `summary`. Ranges SHALL ser `[start, end)` e filtrar o
lado correspondente (`destination`/`source`). `summary=true` SHALL agregar por
`(src, dst, len, cpu, channel, pc)` e devolver grupos com `count`, em vez da lista crua.
Sem filtros, o comportamento SHALL permanecer compatível (`dma_trace_read(seconds)`).

#### Scenario: Só VRAM
- **WHEN** o agente lê o trace com `dst_range=[0x06200000, 0x06220000]`
- **THEN** o resultado não inclui transfers de áudio (`0x07000400`)

#### Scenario: Filtros combinados
- **WHEN** o agente filtra por `cpu="arm9"`, `channel=1` e `min_len=64`
- **THEN** só transfers do ARM9, canal 1 e com `length >= 64` aparecem

#### Scenario: Summary
- **WHEN** o agente pede `summary=true`
- **THEN** recebe grupos por `(src,dst,len,cpu,channel,pc)` com contagem, sem a lista crua

#### Scenario: Limite de itens
- **WHEN** o agente informa `max_items=N` e há mais de N transfers
- **THEN** no máximo N transfers são devolvidos

#### Scenario: Parâmetro inválido
- **WHEN** `dst_range` não tem dois inteiros, `start > end`, `cpu` é inválido, `channel`
  está fora de 0..3, `min_len < 0` ou `max_items <= 0`
- **THEN** a tool retorna `error` + `hint`
