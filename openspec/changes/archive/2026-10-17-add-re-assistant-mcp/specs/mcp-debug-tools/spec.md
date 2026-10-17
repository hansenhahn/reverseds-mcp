## Purpose

Expõe o stub GDB do melonDS como tools MCP de depuração: memória, registradores,
breakpoints, watchpoints e controle de execução — o lado "entender o código".

## ADDED Requirements

### Requirement: Leitura e escrita de memória

O MCP SHALL permitir ler e escrever memória emulada por endereço e tamanho.

#### Scenario: Ler memória
- **WHEN** o agente lê N bytes de um endereço
- **THEN** recebe os bytes

#### Scenario: Escrever memória
- **WHEN** o agente escreve bytes num endereço
- **THEN** a memória emulada passa a conter esses bytes

### Requirement: Registradores

O MCP SHALL permitir ler (e escrever) registradores do core conectado.

#### Scenario: Ler o PC
- **WHEN** o agente lê o registrador PC
- **THEN** recebe o valor atual

### Requirement: Breakpoints e watchpoints

O MCP SHALL permitir criar e remover breakpoints de código e watchpoints de
leitura/escrita/acesso (hardware).

#### Scenario: Watchpoint de escrita
- **WHEN** o agente cria um watchpoint de escrita num endereço e continua a execução
- **THEN** o MCP reporta a parada quando o endereço é escrito

#### Scenario: Breakpoint de código
- **WHEN** o agente cria um breakpoint num endereço e continua
- **THEN** o MCP reporta a parada ao atingir o endereço

### Requirement: Controle de execução

O MCP SHALL permitir continuar, dar passo (step) e interromper a execução.

#### Scenario: Interromper
- **WHEN** o agente pede para interromper
- **THEN** a execução para e o estado atual fica acessível
