## Purpose

Adiciona **desassemblagem** (ARM/Thumb) às tools de depuração, para o agente ler o código
que está sendo executado diretamente pelo MCP.

## ADDED Requirements

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
