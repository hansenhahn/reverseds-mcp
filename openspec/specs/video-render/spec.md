# video-render Specification

## Purpose

Renderiza camadas específicas do vídeo pelo renderer do próprio emulador, para o agente
identificar onde um conteúdo está sem reimplementar BG/OBJ/3D à mão.

## Requirements

### Requirement: Render de uma camada

O sistema SHALL permitir renderizar uma camada específica — engine (`A`/`B`) × `BG0-3`/
`OBJ`/`3D` — e devolver o quadro resultante, podendo escolher as telas (`top`/`bottom`/
`both`) e o formato (`rgba8`/`bgra8`).

#### Scenario: Render de OBJ do engine B
- **WHEN** o agente pede o render da camada `OBJ` do engine `B`
- **THEN** recebe o quadro só com essa camada, composto pelo renderer do emulador

#### Scenario: Frame congelado
- **WHEN** o jogo está pausado num frame
- **THEN** o render da camada corresponde àquele frame congelado (sem avançá-lo)

#### Scenario: Combinação inválida
- **WHEN** a combinação engine × camada não existe (ex.: `3D` no engine `B`)
- **THEN** o sistema reporta erro claro

### Requirement: Renderer do emulador como oráculo

O render SHALL usar o renderer do próprio melonDS, e NÃO SHALL reimplementar a composição.

#### Scenario: Coerência com a exibição
- **WHEN** a camada é renderizada
- **THEN** o resultado corresponde ao que o emulador usaria ao exibir aquela camada

### Requirement: Render sem alterar a emulação

O render SHALL NOT executar código da CPU nem alterar o quadro exibido; o emulador SHALL
permanecer rodando (ou pausado) como estava, mesmo com renders repetidos.

#### Scenario: Emulador continua rodando
- **WHEN** o agente renderiza camadas com o emulador rodando, repetidamente
- **THEN** o emulador continua rodando e interativo após os renders

#### Scenario: Pausa preservada
- **WHEN** o agente renderiza camadas com o emulador pausado
- **THEN** o emulador permanece pausado (um único resume volta a rodar)
