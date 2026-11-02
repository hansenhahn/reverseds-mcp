## ADDED Requirements

### Requirement: Hit log com acesso exato

Com o hit log ligado, cada hit de watchpoint/breakpoint de CPU SHALL registrar, além de
`pc`/`addr`/`kind`: `pc_fault` (a instrução que acessou), `width` (1/2/4 bytes) e `rmw`
(booleano, reservado para RMW). O hit de DMA SHALL registrar o **destino real** em `addr`,
`width = len`, `pc_fault = pc` e `kind = dma-write`. `gdb.hits.read` SHALL devolver esses
campos; `pc`/`addr`/`kind` continuam presentes para compatibilidade.

#### Scenario: Store de CPU
- **WHEN** um `str`/`strh`/`strb` atinge um watchpoint de escrita
- **THEN** o hit traz `pc_fault` da instrução, `width` correspondente e `addr` do acesso

#### Scenario: Leitura de byte adjacente
- **WHEN** dois acessos de byte caem na mesma palavra alinhada
- **THEN** `access`/`width` distinguem os acessos quando o barramento fornece o endereço

#### Scenario: Hit de DMA
- **WHEN** um DMA preenche uma faixa vigiada
- **THEN** o hit `dma-write` traz o destino real, `width=len` e o PC programador

#### Scenario: Payload legado
- **WHEN** um hit não traz os campos novos
- **THEN** o consumidor pode assumir `pc_fault=pc` e `width=0` (compatibilidade)
