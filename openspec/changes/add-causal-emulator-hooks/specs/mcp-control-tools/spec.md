## ADDED Requirements

### Requirement: Tool de cold reset

O MCP SHALL expor `emu_reset`, que reinicia a máquina via `emu.reset` e retorna `ok`. A tool
SHALL NOT desconectar o gdb; com o debugger anexado, a CPU fica parada na entrada de boot
determinística até o agente retomar.

#### Scenario: Reset com debugger
- **WHEN** o agente chama `emu_reset` com o gdb anexado
- **THEN** o reset é aplicado, a CPU fica parada na entrada de boot e os
  breakpoints/watchpoints continuam ativos

#### Scenario: Reset sem o emulador
- **WHEN** o canal de controle não responde
- **THEN** a tool retorna `error` + `hint` para verificar se o melonDS está rodando
