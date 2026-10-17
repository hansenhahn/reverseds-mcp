## ADDED Requirements

### Requirement: Controle responsivo com o debugger anexado

Enquanto o stub GDB tem o alvo **parado**, o canal de controle SHALL permanecer
responsivo: as operações de controle (captura, savestate, input, frame-step) SHALL ser
atendidas, sem exigir que o agente desconecte o debugger.

#### Scenario: Capturar com o debugger parado
- **WHEN** o gdb está anexado e o alvo haltado, e o agente pede uma captura
- **THEN** a captura retorna o framebuffer atual, sem expirar

#### Scenario: Savestate com o debugger parado
- **WHEN** o alvo está haltado pelo gdb e o agente salva o estado
- **THEN** o savestate é gravado

#### Scenario: Frame-step com o debugger anexado
- **WHEN** o gdb está anexado e o agente pede para avançar quadros
- **THEN** a operação é atendida (não expira)

### Requirement: A emulação não avança com a CPU parada

Enquanto o depurador mantém o alvo parado, a emulação NÃO SHALL avançar quadros; o laço
SHALL apenas atender o canal de controle.

#### Scenario: CPU parada não avança
- **WHEN** o depurador mantém o alvo parado
- **THEN** nenhum quadro é emulado até o agente retomar (via gdb ou `emu.resume`)
