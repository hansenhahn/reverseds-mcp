## MODIFIED Requirements

### Requirement: Avanço determinístico de quadros

O sistema SHALL avançar **exatamente `N` quadros** (`N ≥ 1`) e **cessar parado**, com o
framebuffer do último quadro composto, **mesmo com o debugger conectado**. A operação SHALL
ser aplicada na thread de emulação, SHALL bloquear até os `N` quadros terem sido emulados, e
o número avançado SHALL ser **exato** (sem overshoot por latência do cliente). Quando pedido
com captura, o snapshot 3D do **quadro final** SHALL ser copiado no VBlank, antes do halt, na
mesma operação.

#### Scenario: Avançar N quadros
- **WHEN** o agente pede para avançar `N` quadros
- **THEN** a emulação avança exatamente `N` quadros e para no vblank, com o framebuffer composto

#### Scenario: Com o debugger conectado
- **WHEN** o debugger está conectado e o agente pede `N` quadros
- **THEN** a emulação avança **exatamente `N`** quadros e cessa parada (o stub não bloqueia o avanço)

#### Scenario: Termina pausado
- **WHEN** a operação conclui
- **THEN** a emulação está parada — uma captura logo depois reflete o **mesmo** quadro (não andou) e o debugger pode inspecionar; retoma no `continue` do debugger ou num novo `step_frame`

#### Scenario: Avanço com captura 3D
- **WHEN** o agente pede para avançar `N` quadros com captura
- **THEN** o snapshot 3D descreve o quadro final e pode ser lido com o alvo parado, sem nova espera de VBlank

## ADDED Requirements

### Requirement: Status e contador de quadros

O sistema SHALL permitir consultar, **com a emulação parada**, se ela está rodando ou haltada,
o frame counter atual e o frame do último snapshot 3D. O contador SHALL ser lido de forma
consistente na thread de emulação e SHALL NOT adicionar carga por quadro quando não
consultado.

#### Scenario: Consultar parado
- **WHEN** o alvo está haltado e o agente consulta o status
- **THEN** recebe o estado de parada e o frame counter congelado, sem expirar

#### Scenario: Sem custo por quadro
- **WHEN** nenhum cliente consulta o status
- **THEN** o laço de quadro não executa trabalho adicional
