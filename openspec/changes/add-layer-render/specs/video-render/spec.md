## Purpose

Renderiza camadas específicas do vídeo pelo renderer do próprio emulador, para o agente
identificar onde um conteúdo está sem reimplementar BG/OBJ/3D à mão.

## ADDED Requirements

### Requirement: Render de uma camada

O sistema SHALL permitir renderizar uma camada específica — engine (`A`/`B`) × `BG0-3`/
`OBJ`/`3D` — e devolver o quadro resultante.

#### Scenario: Render de OBJ do engine B
- **WHEN** o agente pede o render da camada `OBJ` do engine `B`
- **THEN** recebe o quadro só com essa camada, composto pelo renderer do emulador

#### Scenario: Combinação inválida
- **WHEN** a combinação engine × camada não existe (ex.: `BG0` 3D no engine `B`)
- **THEN** o sistema reporta erro claro

### Requirement: Renderer do emulador como oráculo

O render SHALL usar o renderer do próprio melonDS, e NÃO SHALL reimplementar a composição.

#### Scenario: Coerência com a exibição
- **WHEN** a camada é renderizada
- **THEN** o resultado corresponde ao que o emulador usaria ao exibir aquela camada
