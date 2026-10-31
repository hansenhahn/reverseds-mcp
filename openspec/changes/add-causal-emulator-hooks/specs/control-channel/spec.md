## ADDED Requirements

### Requirement: Cold reset

O canal SHALL expor `emu.reset` para reiniciar a máquina de forma determinística. O reset
SHALL preservar os breakpoints/watchpoints do stub GDB. Com o gdb conectado e a CPU parada, o
reset SHALL deixar a CPU parada em um ponto de boot determinístico (observado em `0x02000800`
no KH) até o agente retomar; sem gdb, o emulador SHALL voltar a rodar.

#### Scenario: Reset com o debugger anexado
- **WHEN** o agente chama `emu.reset` com o gdb anexado e BPs armados
- **THEN** o PC vai para a entrada de boot determinística, a CPU permanece parada e os BPs
  continuam listados

#### Scenario: Reset sem o debugger
- **WHEN** o agente chama `emu.reset` sem gdb anexado
- **THEN** a máquina reinicia e volta a executar

#### Scenario: Preservar watchpoints
- **WHEN** há watchpoints de hardware ativos e o agente reinicia
- **THEN** os watchpoints continuam ativos depois do reset

### Requirement: Hit log

O canal SHALL expor `gdb.hits.start`, `gdb.hits.stop`, `gdb.hits.read` e `gdb.hits.clear`
por core (`arm9`/`arm7`). Com o log ligado, hits de breakpoint e watchpoint SHALL ser
registrados em um ring buffer **sem parar a execução**, com contagem de descartados; a
leitura SHALL devolver `pc`, `addr` e `kind`.

#### Scenario: Hit sem parar
- **WHEN** o log está ligado e um breakpoint/watchpoint é atingido
- **THEN** o hit é registrado e a CPU continua executando

#### Scenario: Ler e limpar
- **WHEN** o agente lê o log e depois o limpa
- **THEN** recebe os hits acumulados e uma leitura seguinte volta vazia

#### Scenario: Ring cheio
- **WHEN** mais hits ocorrem do que a capacidade do ring
- **THEN** os mais antigos são descartados e a contagem de descartados aumenta

#### Scenario: Core errado
- **WHEN** o agente pede o log de um core inválido
- **THEN** o canal retorna erro claro

### Requirement: Watchpoint de escritas de DMA

Watchpoints de escrita/acesso SHALL considerar também escritas de DMA. Se o destino de um
DMA intersecta a faixa vigiada, o stub SHALL registrar/disparar o watchpoint. Com o hit log
ligado, o hit SHALL ser registrado sem parar e com o PC da instrução que programou o DMA;
sem o log, o stub SHALL parar como em um watchpoint normal.

#### Scenario: DMA escreve na VRAM vigiada
- **WHEN** um DMA escreve em uma faixa coberta por um watchpoint de escrita
- **THEN** o watchpoint é considerado atingido (stop ou hit log, conforme o modo)

#### Scenario: Hit log de DMA
- **WHEN** o log está ligado e um DMA escreve na faixa vigiada
- **THEN** o log recebe um hit `dma-write` com o PC do programador do DMA

#### Scenario: Sem watchpoint
- **WHEN** não há watchpoints de escrita e um DMA ocorre
- **THEN** a emulação segue normalmente, sem custo relevante
