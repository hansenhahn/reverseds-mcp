# frame-control Specification

## Purpose

Permite ao agente avançar a emulação quadro-a-quadro e parar de forma determinística no
vblank (com o framebuffer já composto), para congelar e observar um frame exato.

## Requirements

### Requirement: Avanço determinístico de quadros

O sistema SHALL permitir pausar, avançar exatamente `N` quadros (`N ≥ 1`) e parar, com o
framebuffer do último quadro já composto. A operação SHALL bloquear até os `N` quadros
terem sido emulados.

#### Scenario: Avançar N quadros
- **WHEN** o agente pede para avançar `N` quadros
- **THEN** a emulação avança exatamente `N` quadros e para no vblank, com o framebuffer composto

#### Scenario: Termina pausado
- **WHEN** a operação conclui
- **THEN** a emulação está pausada (não avança até um `emu.resume`)

### Requirement: Execução na thread de emulação

A operação SHALL ser aplicada na thread de emulação, e NÃO SHALL adicionar carga por
quadro quando não há avanço em andamento.

#### Scenario: Sem uso, sem custo
- **WHEN** nenhum avanço está em andamento
- **THEN** o laço de quadro não executa trabalho adicional
