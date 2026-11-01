## Purpose

Oferece uma janela de inspeção interativa de OAM/OBJ no frontend do melonDS, para o humano
ver sprites, atributos e tiles sem pedir dump/render ao agente, sem alterar a emulação.

## ADDED Requirements

### Requirement: Abrir a janela

O frontend SHALL expor **System → OAM viewer** quando houver um cartucho carregado. A janela
SHALL ser read-only e SHALL NOT alterar OAM, VRAM ou paleta.

#### Scenario: Abrir com jogo
- **WHEN** há um cartucho e o usuário escolhe System → OAM viewer
- **THEN** a janela abre com os 128 slots do engine selecionado

#### Scenario: Sem jogo
- **WHEN** não há cartucho carregado
- **THEN** a ação fica desabilitada

#### Scenario: Somente leitura
- **WHEN** o usuário interage com grid, engine ou freeze
- **THEN** nenhum byte de OAM/VRAM/paleta é escrito

### Requirement: Seleção de engine

A janela SHALL permitir alternar entre **Engine A** e **Engine B**, recarregando OAM, tiles e
paleta do engine escolhido.

#### Scenario: Trocar engine
- **WHEN** o usuário seleciona Engine B
- **THEN** o grid, os detalhes e o preview passam a refletir o OAM da engine B

### Requirement: Grid de OAM

A janela SHALL mostrar os 128 slots em uma grade (16×8), com thumbnail dos sprites em uso e
indicação visual dos slots livres/inválidos, além de destaque no slot selecionado.

#### Scenario: Slots em uso e livres
- **WHEN** o OAM tem entradas válidas e livres
- **THEN** as válidas mostram thumbnail e as livres são indicadas visualmente

#### Scenario: Selecionar um slot
- **WHEN** o usuário clica em um slot
- **THEN** aquele slot fica destacado e seus detalhes/preview são atualizados

#### Scenario: Bitmap OBJ
- **WHEN** o slot selecionado é um bitmap OBJ (`mode=3`)
- **THEN** o grid/preview indicam que esse modo não é renderizado no POC

### Requirement: Detalhes do OAM

A janela SHALL mostrar, para o slot selecionado, os campos do GBATEK: número, X/Y,
tamanho, OAM Data (3 words), OAM Address, Tile Address, OBJ Mode, OBJ Type, Palette, Priority,
Flip H/V, Mosaic, Rot/Scal, A-D e R/S Address.

#### Scenario: Detalhes coerentes
- **WHEN** um slot é selecionado
- **THEN** os detalhes correspondem aos atributos lidos do OAM

#### Scenario: Affine
- **WHEN** o slot é affine
- **THEN** A-D e R/S Address são mostrados e o Flip H/V não se aplica

### Requirement: Preview

A janela SHALL mostrar um preview ampliado do sprite selecionado com bounding box e as
dimensões; para affine double-size, SHALL indicar a área double-size.

#### Scenario: Sprite normal
- **WHEN** um sprite normal é selecionado
- **THEN** o preview mostra os pixels e a bounding box do tamanho do sprite

#### Scenario: Affine double-size
- **WHEN** um sprite affine com double-size é selecionado
- **THEN** o preview mostra o sprite não rotacionado e a caixa tracejada double-size

### Requirement: Freeze

A janela SHALL oferecer **Freeze** para pausar a emulação durante a inspeção, restaurando o
estado anterior ao fechar/desmarcar.

#### Scenario: Congelar
- **WHEN** o usuário marca Freeze
- **THEN** a emulação pausa e o viewer continua atualizando a partir do estado parado

#### Scenario: Descongelar/fechar
- **WHEN** o usuário desmarca Freeze ou fecha a janela
- **THEN** a emulação retoma se foi o viewer que a pausou

### Requirement: Atualização sob demanda

A janela SHALL atualizar o conteúdo enquanto estiver visível e SHALL parar o timer ao fechar,
sem custo quando fechada.

#### Scenario: Janela fechada
- **WHEN** a janela é fechada
- **THEN** o timer para e nenhuma leitura adicional é feita
