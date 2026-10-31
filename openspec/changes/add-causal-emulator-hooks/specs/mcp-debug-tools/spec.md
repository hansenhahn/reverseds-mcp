## ADDED Requirements

### Requirement: Tools de hit log

O MCP SHALL expor `hit_log_start(core, capacity)`, `hit_log_stop(core)`,
`hit_log_read(core, clear)` e `hit_log_clear(core)`. A leitura SHALL devolver os hits com
`pc`/`addr` em hexadecimal e `kind` legível (`breakpoint`, `write`, `read`, `access`,
`dma-write`), além de `count` e `dropped`.

#### Scenario: Registrar hits sem parar
- **WHEN** o agente liga o log, arma um breakpoint e continua a execução
- **THEN** os hits são acumulados e o alvo não para em cada um deles

#### Scenario: Ler e limpar
- **WHEN** o agente lê o log com `clear=true`
- **THEN** recebe os hits acumulados e o log fica vazio

#### Scenario: Log de DMA
- **WHEN** um DMA escreve em uma faixa com watchpoint de escrita e o log está ligado
- **THEN** a leitura mostra um hit `dma-write` com o PC do programador do DMA

### Requirement: Watchpoint de DMA/VRAM

Um watchpoint de escrita/acesso criado por `set_watchpoint` SHALL considerar escritas de DMA
no mesmo endereço/faixa; o agente SHALL poder usar `hit_log_*` para capturar o programador do
DMA sem parar a execução.

#### Scenario: Watchpoint de VRAM preenchida por DMA
- **WHEN** o agente arma um watchpoint de escrita em uma faixa de VRAM e um DMA a preenche
- **THEN** o watchpoint é atingido (stop ou hit log) e o agente consegue correlacionar a
  origem via `dma_trace`/hit log
