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

### Requirement: Macro de tap

O MCP SHALL oferecer `input_tap(mask, ms)`, que pressiona a(s) tecla(s) da máscara, aguarda
`ms` milissegundos e solta. O input SHALL ser solto ao final, mesmo em erro.

#### Scenario: Tap de Start
- **WHEN** o agente chama `input_tap` com a máscara de Start e 100 ms
- **THEN** a tecla é pressionada e solta, e o jogo processa como um toque

### Requirement: Macro de sequência

O MCP SHALL oferecer `input_sequence(steps)` que executa uma lista ordenada de passos
`{mask|touch, ms, after_ms}`, cada um segurando o input, aguardando `ms`, soltando e
aguardando `after_ms`. O tempo total SHALL ser limitado por um teto de sanidade. Ao final
(ou em erro) o input SHALL ser solto.

#### Scenario: Sequência de botões
- **WHEN** o agente envia uma sequência de passos de botão
- **THEN** os passos são executados em ordem e o input é solto no fim

#### Scenario: Erro no meio
- **WHEN** uma chamada ao canal falha no meio da sequência
- **THEN** o input é solto e o MCP reporta o erro

#### Scenario: Passo só de espera
- **WHEN** um passo não traz nem `mask` nem `touch`
- **THEN** a sequência apenas aguarda, sem pressionar

### Requirement: Macro de toque

O MCP SHALL oferecer `input_touch_tap(x, y, ms)`, que toca `(x, y)` na **tela de baixo**
(engine B), aguarda `ms` e solta; e `input_sequence` SHALL aceitar passos de **toque**
(`{touch: [x, y], ms, after_ms}`), **intercaláveis** com passos de botão. As coordenadas
SHALL estar dentro da tela (`0<=x<256`, `0<=y<192`); o input SHALL ser solto ao final, mesmo
em erro.

#### Scenario: Tap de toque (jogo touch-only)
- **WHEN** o agente chama `input_touch_tap` num ponto da tela de baixo
- **THEN** o toque é aplicado e solto, e o jogo (touch-only) reage

#### Scenario: Passo de toque numa sequência
- **WHEN** um passo traz `touch` em vez de `mask`
- **THEN** a sequência toca a tela por `ms`, solta e segue (podendo intercalar com botões)

#### Scenario: Coordenada inválida
- **WHEN** o toque está fora de `0<=x<256` / `0<=y<192`
- **THEN** o sistema reporta erro claro
