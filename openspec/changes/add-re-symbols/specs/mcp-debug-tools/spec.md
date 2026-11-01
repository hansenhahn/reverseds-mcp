## ADDED Requirements

### Requirement: Disassembly anotado

`disassemble` SHALL incluir, para cada instrução, o **símbolo** que contém o endereço (quando
houver) e o **símbolo do alvo** de um branch/call (quando o operando contém um endereço e ele
resolve). O `debug_backtrace` SHALL preencher `function` com o símbolo quando o gdb não tiver
resolvido a função.

#### Scenario: Instrução anotada
- **WHEN** o agente desmonta um endereço coberto por `desenha_painel`
- **THEN** a instrução inclui `symbol="desenha_painel"`

#### Scenario: Alvo de chamada anotado
- **WHEN** uma instrução é um `bl`/`blx` para um endereço com símbolo
- **THEN** a instrução inclui o símbolo do alvo

#### Scenario: Backtrace anotado
- **WHEN** o gdb devolve `function=null` para um frame cujo PC está sob um símbolo
- **THEN** o frame é retornado com o nome do símbolo

#### Scenario: Sem símbolo
- **WHEN** o endereço não está coberto por nenhum símbolo
- **THEN** a anotação é `null`/ausente, sem erro
