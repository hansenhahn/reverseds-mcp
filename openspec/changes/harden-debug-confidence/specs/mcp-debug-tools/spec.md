## MODIFIED Requirements

### Requirement: Breakpoints e watchpoints

O MCP SHALL permitir criar e remover breakpoints de código e watchpoints de
leitura/escrita/acesso (hardware). A criação SHALL reportar sucesso para os três tipos de
watchpoint, mesmo quando o gdb responder com o rótulo específico (`Hardware read watchpoint`,
`Hardware access watchpoint`, `Hardware access (read/write) watchpoint`). A listagem SHALL incluir todos os tipos, com número, tipo
normalizado, endereço, condição, estado e se usa **slot de hardware** ou o fallback de
software; a remoção SHALL aceitar qualquer um deles e SHALL reportar erro claro quando o
número não existir.

#### Scenario: Watchpoint de escrita
- **WHEN** o agente cria um watchpoint de escrita num endereço e continua a execução
- **THEN** o MCP reporta a parada quando o endereço é escrito

#### Scenario: Breakpoint de código
- **WHEN** o agente cria um breakpoint num endereço e continua
- **THEN** o MCP reporta a parada ao atingir o endereço

#### Scenario: Watchpoint de leitura
- **WHEN** o agente cria um watchpoint de leitura e o gdb responde
  `Hardware read watchpoint N`
- **THEN** o MCP retorna o número `N` (sem erro) e a listagem passa a incluir esse watchpoint

#### Scenario: Watchpoint de acesso
- **WHEN** o agente cria um watchpoint de acesso e o gdb responde
  `Hardware access watchpoint N` ou `Hardware access (read/write) watchpoint N`
- **THEN** o MCP retorna o número `N` e a listagem o identifica como acesso

#### Scenario: Fallback de software
- **WHEN** o limite de hardware é atingido e o gdb cria um watchpoint de software
- **THEN** a listagem o identifica como **não** hardware (`hardware=false`) e ele não conta
  como slot ocupado

#### Scenario: Listar e remover watchpoints
- **WHEN** há watchpoints de escrita, leitura e acesso ativos e o agente lista ou remove um
  deles pelo número
- **THEN** a listagem devolve todos com endereço/condição/estado e a remoção remove o
  escolhido, sem afetar os demais

#### Scenario: Remover número inexistente
- **WHEN** o agente remove um número que não existe
- **THEN** o MCP retorna `error` + `hint` (não um sucesso silencioso)

## ADDED Requirements

### Requirement: Diagnóstico de slots de hardware

O MCP SHALL oferecer `debug_slots` para o core conectado, informando o limite de watchpoints
de hardware, quantos **slots de hardware** estão em uso, quantos estão livres, quantos
watchpoints estão no **fallback de software** e a lista de watchpoints ativos por tipo.
Watchpoints de software SHALL NOT contar como slot de hardware. Quando a criação de um
watchpoint falhar por falta de recursos (ou tipo não suportado), o MCP SHALL retornar
`error` + `hint` indicando como inspecionar/liberar os slots.

#### Scenario: Slots após criar watchpoints
- **WHEN** o agente cria dois watchpoints e chama `debug_slots`
- **THEN** o resultado informa limite, dois em uso, os livres correspondentes e a lista dos
  dois watchpoints

#### Scenario: Slots livres
- **WHEN** nenhum watchpoint está ativo e o agente chama `debug_slots`
- **THEN** o resultado informa zero em uso e todos os slots livres

#### Scenario: Fallback não consome slot
- **WHEN** há quatro watchpoints de hardware e o gdb cria um quinto em modo software
- **THEN** `debug_slots` mantém `watchpoints_used=4`, `free=0` e reporta
  `software_watchpoints=1`

#### Scenario: Esgotamento de recursos
- **WHEN** o gdb recusa a criação de um watchpoint por falta de recursos de hardware
- **THEN** o MCP retorna `error` + `hint` apontando `debug_slots`/`list_breakpoints` para
  liberar slots

#### Scenario: Núcleo conectado
- **WHEN** o debugger está conectado ao ARM9 ou ao ARM7 e o agente chama `debug_slots`
- **THEN** o resultado identifica o core em uso

### Requirement: Endereço normalizado no retorno

`set_breakpoint` e `mem_write` SHALL incluir no retorno o endereço normalizado efetivamente
usado na operação, para confirmar contra erro de aritmética.

#### Scenario: Criar breakpoint
- **WHEN** o agente cria um breakpoint em um endereço
- **THEN** o retorno inclui o número e o endereço normalizado (`0x...`)

#### Scenario: Escrever memória
- **WHEN** o agente escreve bytes em um endereço
- **THEN** o retorno inclui o endereço normalizado e o tamanho escrito
