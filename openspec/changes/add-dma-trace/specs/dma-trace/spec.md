## Purpose

Expõe, em tempo real, as transferências de DMA (`src`, `dst`, `length`, `cnt`) e o `pc`
que as programou, para o agente ligar um upload de VRAM ao código que o disparou.

## ADDED Requirements

### Requirement: Registro de cada DMA

O sistema SHALL registrar, no **início** de cada transferência de DMA, um item com
`src`, `dst`, `length`, `cnt` e o `pc` que programou o canal.

#### Scenario: Uma transferência gera um registro
- **WHEN** um canal DMA inicia uma transferência
- **THEN** um item `{src, dst, length, cnt, pc}` é registrado

#### Scenario: Granularidade por transferência
- **WHEN** um DMA move um bloco de N bytes
- **THEN** é gerado **um** item (não um por palavra movida)

### Requirement: Entrega em lotes

O sistema SHALL acumular os itens e entregá-los em lotes, disparando quando o lote
atingir N itens ou quando decorrer o timeout, o que ocorrer primeiro.

#### Scenario: Lote por tamanho
- **WHEN** o trace acumula N itens
- **THEN** o lote é entregue

#### Scenario: Lote por timeout
- **WHEN** decorre o timeout com itens pendentes
- **THEN** o lote parcial é entregue

### Requirement: Subscrição do trace

O sistema SHALL permitir iniciar e parar o trace de DMA.

#### Scenario: Iniciar e parar
- **WHEN** o agente inicia o trace, o jogo roda e depois o agente para o trace
- **THEN** os DMAs ocorridos no intervalo são reportados

### Requirement: Carga mínima na thread de emulação

O hook de DMA SHALL ser O(1) e SHALL NOT alocar; a codificação e o envio ocorrem fora da
thread de emulação; sem assinante, o custo SHALL ser desprezível.

#### Scenario: Sem assinante, sem custo
- **WHEN** nenhum cliente assina o trace
- **THEN** o hook não executa trabalho adicional por DMA
