# cart-trace Specification

## Purpose
Expõe, em tempo real, as leituras que o jogo faz do cartucho (endereço, tamanho e
comando), acumuladas em lotes por N/timeout e entregues pelo canal de controle,
para o agente entender carregamento/streaming sem perder nenhuma leitura.

## Requirements

### Requirement: Registro das leituras do cartucho

O sistema SHALL registrar, no início de cada transferência de leitura do
cartucho, um item com **endereço**, **tamanho** e **comando**. O registro SHALL
ocorrer no ponto da transferência (não por palavra), de modo que o volume seja
proporcional ao número de transferências.

#### Scenario: Uma transferência gera um registro
- **WHEN** o jogo inicia uma leitura de ROM (AUXSPI/ROMCNT)
- **THEN** um item `{address, length, command}` é adicionado ao trace

#### Scenario: Granularidade por transferência
- **WHEN** uma transferência lê um bloco de N bytes
- **THEN** é gerado **um** item (não um por palavra lida)

### Requirement: Batching por N ou timeout

O sistema SHALL acumular os itens e entregá-los em **lotes**, disparando o envio
quando o lote atingir **N itens** **ou** quando decorrer o **timeout**
configurado, o que ocorrer primeiro.

#### Scenario: Lote cheio
- **WHEN** o trace acumula N itens
- **THEN** o lote é entregue imediatamente

#### Scenario: Timeout com lote parcial
- **WHEN** menos de N itens foram acumulados e o timeout decorre
- **THEN** o lote parcial é entregue

### Requirement: Subscrição do trace (start/stop)

O trace SHALL ser **opt-in**: desligado por padrão, sem custo. O cliente SHALL
poder **subscrever** (`cart.trace.start`, com `{batch, timeout_ms}`) e
**cancelar a subscrição** (`cart.trace.stop`). Haverá **um trace ativo por vez**;
enquanto houver um assinante, o registro fica ativo e os lotes são entregues a
ele.

#### Scenario: Desligado por padrão
- **WHEN** nenhum cliente subscreveu
- **THEN** nenhuma leitura é registrada e não há custo

#### Scenario: Subscrever
- **WHEN** o cliente chama `cart.trace.start` com `{batch, timeout_ms}`
- **THEN** o registro fica ativo e o cliente passa a receber lotes

#### Scenario: Cancelar a subscrição
- **WHEN** o cliente chama `cart.trace.stop`
- **THEN** o cliente deixa de receber lotes e o registro para

#### Scenario: Já existe um trace ativo
- **WHEN** um cliente chama `cart.trace.start` enquanto já há um trace ativo
- **THEN** o servidor responde com erro (trace já ativo)

### Requirement: Sem perda de leituras

O sistema SHALL preservar todas as leituras registradas. Se o buffer atingir um
limite, o sistema SHALL crescer ou sinalizar **overflow** explicitamente — nunca
descartar itens silenciosamente.

#### Scenario: Buffer no limite
- **WHEN** o número de itens acumulados atinge o limite do buffer
- **THEN** o sistema sinaliza overflow ao cliente (em vez de descartar em silêncio)

### Requirement: Ordem preservada

Os itens SHALL ser entregues na **ordem** em que ocorreram.

#### Scenario: Ordem das transferências
- **WHEN** duas transferências ocorrem em sequência
- **THEN** os itens chegam ao cliente na mesma ordem

### Requirement: Carga mínima na thread de emulação

A thread de emulação SHALL apenas **anexar** o item e **sinalizar** o lote; ela
NÃO SHALL serializar JSON nem realizar I/O de socket. Com o trace desabilitado,
NÃO SHALL haver custo adicional.

#### Scenario: Anexar sem serializar
- **WHEN** uma leitura é registrada com o trace ativo
- **THEN** a thread de emulação apenas anexa o item ao buffer (sem JSON/socket)

#### Scenario: Desabilitado, sem custo
- **WHEN** o trace está desabilitado
- **THEN** nenhum registro é coletado e não há custo por transferência
