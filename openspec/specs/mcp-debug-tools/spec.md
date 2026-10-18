# mcp-debug-tools Specification

## Purpose

Expõe o stub GDB do melonDS como tools MCP de depuração: memória, registradores,
breakpoints, watchpoints e controle de execução — o lado "entender o código".

## Requirements

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

### Requirement: Desassemblagem

O MCP SHALL oferecer `disassemble(addr, count, mode)` que lê memória no core conectado e
devolve uma lista ordenada de instruções, cada uma com **endereço**, **bytes**, **mnemônico**
e **operandos**. O `mode` SHALL ser `arm` ou `thumb` (default `arm`).

#### Scenario: Desmontar o PC (ARM)
- **WHEN** o agente pede `disassemble` em um endereço com `count` instruções no modo `arm`
- **THEN** recebe as instruções na ordem, cada uma com mnemônico e operandos

#### Scenario: Modo Thumb
- **WHEN** o agente desmonta código com `mode="thumb"`
- **THEN** as instruções são interpretadas em Thumb (16/32 bits)

#### Scenario: Alvo em execução
- **WHEN** o alvo está rodando (não parado) e o agente pede `disassemble`
- **THEN** o MCP responde com erro claro indicando que é preciso parar/esperar antes
