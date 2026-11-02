## ADDED Requirements

### Requirement: Símbolos cientes de overlay

O MCP SHALL indexar símbolos por `(addr, overlay)` e permitir definir, listar e consultar símbolos
por overlay. `symbol_define(addr, name, overlay=N)` SHALL criar/atualizar apenas aquele par
(endereço, overlay), sem apagar o mesmo endereço em outra overlay. `symbol_lookup(addr, overlay=None)`
e `symbol_list(kind=None, overlay=None)` SHALL usar a overlay explícita; sem ela, SHALL usar a
seleção ativa (`overlay_select`) e, se ainda houver mais de um símbolo no mesmo endereço, SHALL
retornar ambiguidade (`ambiguous=true` + lista) em vez de escolher o primeiro. Símbolos legados com
`overlay=null` SHALL continuar válidos como globais (fallback).

#### Scenario: Mesmo endereço em overlays diferentes
- **WHEN** o agente define `0x020A11C4` como `fn_22` (overlay 22) e `fn_25` (overlay 25)
- **THEN** os dois símbolos coexistem e nenhum apaga o outro

#### Scenario: Consulta com overlay explícita
- **WHEN** o agente consulta `0x020A11C4` com `overlay=25`
- **THEN** recebe `fn_25`, mesmo existindo `fn_22` no mesmo endereço

#### Scenario: Consulta com overlay ativa
- **WHEN** o agente selecionou a overlay 25 e consulta o endereço sem `overlay=`
- **THEN** a resolução usa a 25

#### Scenario: Consulta ambígua
- **WHEN** há símbolos de 22 e 25 no mesmo endereço, sem overlay explícita/ativa
- **THEN** a consulta retorna `ambiguous=true` e a lista de símbolos, sem escolher um silenciosamente

#### Scenario: Símbolo global
- **WHEN** existe um símbolo legado com `overlay=null` e não há específico para a overlay consultada
- **THEN** o símbolo global é usado como fallback

#### Scenario: Listar por overlay
- **WHEN** o agente lista símbolos com `overlay=25`
- **THEN** a lista contém apenas os símbolos da 25

### Requirement: Carregamento de mapas por overlay

`symbol_load(path, merge=True, overlay=None)` SHALL permitir marcar todos os símbolos de um `.map`
com uma overlay. Com `merge=true`, SHALL mesclar na tabela sem afetar outras overlays. Com
`merge=false` e `overlay=N`, SHALL substituir somente os símbolos da overlay N, preservando globais e
outras overlays. Com `merge=false` e `overlay=None`, SHALL substituir a tabela inteira.

#### Scenario: Carregar mapa da overlay 25
- **WHEN** o agente carrega `overlay25.map` com `overlay=25` e `merge=true`
- **THEN** os símbolos entram marcados com 25, preservando os da 22

#### Scenario: Recarregar mapa da overlay 25
- **WHEN** o agente carrega outro mapa com `overlay=25` e `merge=false`
- **THEN** os símbolos antigos da 25 são substituídos, mas os da 22 e os globais permanecem

#### Scenario: Substituir a tabela inteira
- **WHEN** o agente carrega um `.map` com `merge=false` e sem `overlay=`
- **THEN** a tabela inteira é substituída (comportamento anterior)

### Requirement: Anotação de endereço por overlay

`addr_valid(value, overlay=None)` SHALL anotar **cada candidato de overlay** com o símbolo daquele
overlay e SHALL preencher o símbolo do topo com a overlay explícita/ativa (ou com o único candidato).
Quando não houver seleção e houver mais de um símbolo no mesmo endereço, o símbolo do topo SHALL ser
`null` (sem escolher um silenciosamente). Símbolos globais (`overlay=null`) SHALL servir de fallback.

#### Scenario: Candidato 22
- **WHEN** o agente valida um endereço coberto por 22 e 25 e há símbolos nos dois
- **THEN** o candidato 22 inclui o símbolo da 22

#### Scenario: Candidato 25
- **WHEN** o mesmo endereço acima é validado
- **THEN** o candidato 25 inclui o símbolo da 25

#### Scenario: Seleção ativa
- **WHEN** a overlay 25 está ativa e o endereço é validado
- **THEN** o símbolo do topo é o da 25

#### Scenario: Sem seleção e ambíguo
- **WHEN** há símbolos de 22 e 25 no mesmo endereço e nenhuma seleção ativa
- **THEN** o símbolo do topo é `null`, mantendo os símbolos por candidato

#### Scenario: Fallback global
- **WHEN** não há símbolo específico da overlay, mas há um global
- **THEN** o candidato usa o símbolo global
