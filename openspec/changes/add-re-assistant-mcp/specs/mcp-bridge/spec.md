## Purpose

Conecta o servidor MCP aos dois canais do melonDS (canal de controle e stub GDB),
cuidando de configuração, escolha de core e erros — sem tocar no emulador.

## ADDED Requirements

### Requirement: Conexão ao canal de controle

O servidor MCP SHALL conectar ao canal de controle do melonDS por socket Unix,
com o caminho configurável, e SHALL reportar erro claro quando o emulador não
estiver disponível.

#### Scenario: Conectar
- **WHEN** o MCP inicia com o caminho do socket configurado
- **THEN** ele consegue chamar `ping` e recebe `{"pong": true}`

#### Scenario: Emulador ausente
- **WHEN** o socket não existe ou não conecta
- **THEN** o MCP reporta um erro claro (sem travar) e permite reconfigurar

### Requirement: Conexão ao gdb (stub GDB)

O servidor MCP SHALL gerenciar um `gdb` (`gdb-multiarch`, com pwndbg) conectado ao
stub GDB (RSP) do core escolhido (ARM9 ou ARM7), com o limite de watchpoint de
hardware aplicado.

#### Scenario: Escolher o core
- **WHEN** o agente pede para depurar o ARM9
- **THEN** o MCP conecta o gdb na porta do ARM9 e passa a operar nesse core

#### Scenario: Watchpoint de hardware garantido
- **WHEN** o gdb é conectado
- **THEN** o limite de watchpoint de hardware é aplicado, de modo que os watchpoints usem hardware

### Requirement: Exposição e descoberta de tools

O servidor MCP SHALL expor as tools das capabilities de controle, depuração e RE,
e SHALL permitir ao agente descobri-las.

#### Scenario: Descoberta de tools
- **WHEN** o agente lista as tools do MCP
- **THEN** aparecem as tools de emulação, depuração e RE
