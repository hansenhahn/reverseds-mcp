## Purpose

Expõe, em tempo real, as transferências de DMA (`src`, `dst`, `length`, `cnt`) e o `pc`
que as programou, para o agente ligar um upload de VRAM ao código que o disparou.

## ADDED Requirements

### Requirement: Registro decodificado de cada DMA

O sistema SHALL registrar, no **início** de cada transferência de DMA, um item
**decodificado**: o `channel`, o **de → para** (`source`/`destination` — endereços e
controles), o `length` em **bytes** e o **controle decodificado** do `DMAxCNT` — pelos
**mesmos nomes de campo do schema GBATEK** (`transfer_32bit`, `src_control`, `dest_control`,
`start_timing`, `repeat`, `irq`, `enable`) — além do `pc` que programou o canal. O item
NÃO SHALL expor o `cnt` como bits crus.

#### Scenario: Uma transferência gera um item decodificado
- **WHEN** um canal DMA inicia uma transferência
- **THEN** um item com `channel`, `source`/`destination` (endereços + controles), `length`
  (bytes), `size`/`start_timing`/`repeat`/`irq` e `pc` é registrado

#### Scenario: De → para abstraído
- **WHEN** um DMA copia da RAM para a VRAM
- **THEN** o item traz `destination.address` em `0x06000000+` e o controle de destino
  (`inc`/`dec`/`fixed`/`inc/reload`) já decodificado

#### Scenario: Controle pelos mesmos nomes do schema
- **WHEN** o `DMAxCNT` é registrado
- **THEN** os campos usam os mesmos nomes do schema GBATEK (`transfer_32bit`,
  `start_timing`, ...), consistentes com o `io_read`

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

### Requirement: Buffer limitado (ring)

O trace SHALL manter um **ring de capacidade fixa** (configurável no início), descartando o
**item mais antigo** ao estourar e reportando a **contagem de descartados** — NÃO SHALL
crescer sem limite. O custo por transferência SHALL permanecer O(1) e sem alocação.

#### Scenario: Estouro do ring
- **WHEN** mais transfers que a capacidade se acumulam sem o cliente drenar
- **THEN** os mais antigos são descartados e o lote reporta quantos foram descartados

#### Scenario: Capacidade configurável
- **WHEN** o agente inicia o trace com `max_items`
- **THEN** o ring usa essa capacidade

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
