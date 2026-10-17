# mcp-control-tools Specification

## Purpose

Expõe o canal de controle do emulador como tools MCP: input, tela, savestate,
pause/resume e trace de cartucho — o lado "jogar e observar".

## Requirements

### Requirement: Tools de input

O MCP SHALL expor tools de input equivalentes aos métodos `input.*` do canal de
controle (teclas, toque, soltar, merge).

#### Scenario: Apertar um botão
- **WHEN** o agente chama a tool de input com o mask do botão
- **THEN** o emulador registra o botão pressionado

#### Scenario: Tocar a tela
- **WHEN** o agente chama a tool de toque com coordenadas
- **THEN** o emulador registra a caneta pressionada nessas coordenadas

### Requirement: Tool de captura de tela (sob demanda)

O MCP SHALL expor a captura de tela **sob demanda** — o agente captura quando
precisa "olhar" — e NÃO SHALL empurrar um stream contínuo de quadros ao agente
(custo de tokens de visão).

#### Scenario: Capturar a tela quando necessário
- **WHEN** o agente chama a tool de captura
- **THEN** recebe uma imagem das telas (top/bottom) no formato pedido

#### Scenario: Sem streaming contínuo
- **WHEN** o agente não pede captura
- **THEN** nenhum quadro é enviado ao agente

### Requirement: Tools de savestate e execução

O MCP SHALL expor salvar/carregar estado e pausar/retomar.

#### Scenario: Salvar e restaurar
- **WHEN** o agente salva e depois carrega um slot
- **THEN** o estado volta ao ponto salvo

### Requirement: Tools de trace de cartucho

O MCP SHALL expor iniciar/parar o trace de leitura do cartucho e obter os lotes
de leituras.

#### Scenario: Monitorar leituras
- **WHEN** o agente inicia o trace e o jogo lê a ROM
- **THEN** o agente recebe as leituras (endereço, tamanho e comando)

### Requirement: Hint de captura

Quando `screen_capture` expira, o MCP SHALL retornar `error` acompanhado de `hint`
indicando que a CPU pode estar haltada (usar `debug_resume`/`debug_disconnect`) ou que o
renderer pode não ser software.

#### Scenario: Captura com a CPU parada
- **WHEN** o agente chama `screen_capture` com o debugger conectado e a CPU parada
- **THEN** a resposta traz `error` e o `hint` correspondente
