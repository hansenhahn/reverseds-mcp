## MODIFIED Requirements

### Requirement: Avanço determinístico de quadros

O sistema SHALL avançar **exatamente `N` quadros** (`N ≥ 1`) e **cessar parado**, com o
framebuffer do último quadro composto, **mesmo com o debugger conectado**. A operação SHALL
ser aplicada na thread de emulação, SHALL bloquear até os `N` quadros terem sido emulados, e
o número avançado SHALL ser **exato** (sem overshoot por latência do cliente).

#### Scenario: Avançar N quadros
- **WHEN** o agente pede para avançar `N` quadros
- **THEN** a emulação avança exatamente `N` quadros e para no vblank, com o framebuffer composto

#### Scenario: Com o debugger conectado
- **WHEN** o debugger está conectado e o agente pede `N` quadros
- **THEN** a emulação avança **exatamente `N`** quadros e cessa parada (o stub não bloqueia o avanço)

#### Scenario: Termina pausado
- **WHEN** a operação conclui
- **THEN** a emulação está parada — uma captura logo depois reflete o **mesmo** quadro (não andou) e o debugger pode inspecionar; retoma no `continue` do debugger ou num novo `step_frame`
