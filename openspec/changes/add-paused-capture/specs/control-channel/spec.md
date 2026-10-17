## ADDED Requirements

### Requirement: Captura com a CPU parada

O sistema SHALL permitir capturar o framebuffer atual mesmo com a CPU **parada**,
renderizando sob demanda; a captura NÃO SHALL depender de a emulação avançar quadros.

#### Scenario: Capturar com a CPU parada
- **WHEN** a CPU está parada (pausada) e o agente pede uma captura
- **THEN** o servidor renderiza e devolve o framebuffer atual, sem expirar

#### Scenario: Render explícito do quadro
- **WHEN** o agente pede um render explícito do quadro corrente
- **THEN** o quadro é composto e retornado, independentemente do laço de emulação
