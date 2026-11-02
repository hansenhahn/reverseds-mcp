## ADDED Requirements

### Requirement: Anotação de símbolos com overlay

As tools de depuração que anotam endereços com símbolos (`disassemble`, `debug_backtrace`,
`find_writer`/`find_reader`, `hit_log_read`, `dma_source`, `args_on_hit` e `contract_check`) SHALL
usar a overlay explícita (quando a tool aceitar) ou a overlay ativa (`overlay_select`) ao resolver
nomes. Quando não houver overlay explícita/ativa e houver mais de um símbolo no mesmo endereço, a
anotação SHALL ser `null` (ou lista de candidatos, quando a tool já expõe lista), nunca um nome de
overlay escolhido silenciosamente. Símbolos globais (`overlay=null`) SHALL servir de fallback.

`disassemble(addr, count, mode, overlay=None)` SHALL aceitar uma overlay explícita e anotar tanto a
instrução quanto o alvo de branch/call com o símbolo daquela overlay.

#### Scenario: Disasm com overlay explícita
- **WHEN** o agente desmonta um endereço com `overlay=25`
- **THEN** as instruções e alvos usam os símbolos da 25 (não os da 22)

#### Scenario: Disasm com overlay ativa
- **WHEN** a overlay 25 está ativa via `overlay_select` e o agente desmonta o endereço
- **THEN** a anotação usa os símbolos da 25

#### Scenario: Hit de watchpoint
- **WHEN** um `find_writer`/`find_reader` para em um PC com símbolos de 22 e 25 e a 25 está ativa
- **THEN** o hit anota o nome da 25

#### Scenario: Ambiguidade sem seleção
- **WHEN** não há overlay explícita/ativa e o PC tem símbolos de 22 e 25
- **THEN** a anotação não escolhe um nome (fica `null`/ambígua), sem inventar overlay

#### Scenario: Fallback global
- **WHEN** não há símbolo específico para a overlay consultada, mas há um global
- **THEN** a anotação usa o símbolo global
