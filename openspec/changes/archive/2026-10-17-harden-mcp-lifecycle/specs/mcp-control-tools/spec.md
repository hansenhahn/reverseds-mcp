## Purpose

Melhora o diagnóstico das tools de controle quando a captura de tela falha por a CPU estar
parada (ou por renderer incompatível).

## ADDED Requirements

### Requirement: Hint de captura

Quando `screen_capture` expira, o MCP SHALL retornar `error` acompanhado de `hint`
indicando que a CPU pode estar haltada (usar `debug_resume`/`debug_disconnect`) ou que o
renderer pode não ser software.

#### Scenario: Captura com a CPU parada
- **WHEN** o agente chama `screen_capture` com o debugger conectado e a CPU parada
- **THEN** a resposta traz `error` e o `hint` correspondente
