## Purpose

Permite ao agente avançar a emulação quadro-a-quadro e parar de forma determinística no
vblank (com o framebuffer já composto), para congelar e observar um frame exato.

## ADDED Requirements

### Requirement: Avanço determinístico de quadros

O sistema SHALL permitir avançar exatamente `N` quadros e parar, com o framebuffer do
último quadro já composto.

#### Scenario: Avançar N quadros
- **WHEN** o agente pede para avançar `N` quadros
- **THEN** a emulação avança exatamente `N` quadros e para no vblank, com o framebuffer composto

### Requirement: Rodar até o vblank

O sistema SHALL permitir rodar até o próximo vblank e parar.

#### Scenario: Parar no vblank
- **WHEN** o agente pede para rodar até o vblank
- **THEN** a emulação para no próximo vblank, com o framebuffer composto

### Requirement: Parar no próximo quadro

O sistema SHALL permitir agendar uma parada no fim do quadro corrente.

#### Scenario: Agendar parada
- **WHEN** o agente agenda parar no próximo quadro
- **THEN** a emulação para ao término do quadro corrente, no vblank

### Requirement: Execução na thread de emulação

As operações de controle de frame SHALL ser aplicadas na thread de emulação, e NÃO SHALL
adicionar carga por quadro quando não há parada agendada.

#### Scenario: Sem uso, sem custo
- **WHEN** nenhuma parada está agendada
- **THEN** o laço de quadro não executa trabalho adicional
