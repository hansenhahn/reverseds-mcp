## ADDED Requirements

### Requirement: Hit log com acesso exato no MCP

`hit_log_read` SHALL devolver, por hit: `pc`, `pc_fault`, `addr`/`access_addr`, `width`,
`rmw`, `kind` e os símbolos de `pc`/`pc_fault` (quando resolvíveis). Quando o payload do
canal não trouxer `pc_fault`/`width`/`rmw`, SHALL usar `pc_fault=pc`, `width=0`,
`rmw=false` (compatibilidade). O MCP SHALL derivar `rmw=true` quando houver um hit `read` e
um `write` com o mesmo `pc_fault` e `access_addr`.

#### Scenario: Store anotado
- **WHEN** o log contém um hit de escrita com `pc_fault`
- **THEN** a leitura mostra `pc_fault`, `fault_pc_symbol`, `access_addr` e `width`

#### Scenario: RMW
- **WHEN** o log contém read+write no mesmo `pc_fault`/`access_addr`
- **THEN** os dois hits trazem `rmw=true`

#### Scenario: Payload antigo
- **WHEN** o canal devolve apenas `pc`/`addr`/`kind`
- **THEN** a leitura continua funcionando com `pc_fault=pc`, `width=0`, `rmw=false`

#### Scenario: DMA
- **WHEN** o log contém um hit `dma-write`
- **THEN** `addr` é o destino real e `width` é o `len`
