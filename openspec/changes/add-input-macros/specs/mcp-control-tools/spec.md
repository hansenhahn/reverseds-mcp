## Purpose

Estende as tools de controle com **macros de input** (tap e sequência), para o agente
automatizar transições de tela de forma confiável.

## ADDED Requirements

### Requirement: Macro de tap

O MCP SHALL oferecer `input_tap(mask, ms)`, que pressiona a(s) tecla(s) da máscara, aguarda
`ms` milissegundos e solta. O input SHALL ser solto ao final, mesmo em erro.

#### Scenario: Tap de Start
- **WHEN** o agente chama `input_tap` com a máscara de Start e 100 ms
- **THEN** a tecla é pressionada e solta, e o jogo processa como um toque

### Requirement: Macro de sequência

O MCP SHALL oferecer `input_sequence(steps)` que executa uma lista ordenada de passos
`{mask, ms, after_ms}`, cada um pressionando, aguardando `ms`, soltando e aguardando
`after_ms`. O tempo total SHALL ser limitado por um teto de sanidade. Ao final (ou em erro)
o input SHALL ser solto.

#### Scenario: Sequência Start→B
- **WHEN** o agente envia `[{mask:Start, ms:100, after_ms:1000}, {mask:B, ms:100, after_ms:0}]`
- **THEN** o jogo entra no menu e volta, re-renderizando o HUD

#### Scenario: Erro no meio
- **WHEN** uma chamada ao canal falha no meio da sequência
- **THEN** o input é solto e o MCP reporta o erro

#### Scenario: Passo só de espera
- **WHEN** um passo não traz `mask`
- **THEN** a sequência apenas aguarda, sem pressionar tecla

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
