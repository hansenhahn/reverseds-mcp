## ADDED Requirements

### Requirement: Backtrace

O MCP SHALL oferecer `debug_backtrace()` que devolve a pilha de chamadas do core conectado
como uma lista ordenada de frames, cada um com o índice (`#`), o `pc` e a `function` (quando o
stub a conhece). O alvo SHALL estar parado; com o alvo em execução, o MCP SHALL responder erro
claro.

#### Scenario: Backtrace com o alvo parado
- **WHEN** o agente pede o backtrace com o alvo parado
- **THEN** recebe os frames em ordem, do mais interno ao mais externo, cada um com `pc`

#### Scenario: Alvo em execução
- **WHEN** o agente pede o backtrace com o alvo rodando
- **THEN** o MCP responde erro claro indicando que é preciso parar/esperar antes

### Requirement: Lista de breakpoints

O MCP SHALL oferecer `list_breakpoints()` que devolve os breakpoints e watchpoints ativos,
cada um com o `number`, o `type` (breakpoint ou watchpoint), o `address`, a `condition`
(quando houver) e se está `enabled`. A lista SHALL refletir o estado atual do stub.

#### Scenario: Listar após criar
- **WHEN** o agente cria um breakpoint e pede a lista
- **THEN** a lista contém um item com o número retornado na criação, o endereço e o tipo

#### Scenario: Lista vazia
- **WHEN** não há breakpoints/watchpoints ativos
- **THEN** a lista volta vazia (sem erro)
