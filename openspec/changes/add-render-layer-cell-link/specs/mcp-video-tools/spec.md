## ADDED Requirements

### Requirement: Correlação tela → célula

O MCP SHALL expor `cell_at_screen(engine, bg, x, y)` que converta um pixel da tela do engine
(0..255, 0..191) para a célula do mapa, considerando `BGxHOFS/VOFS` e o wrap do mapa. O
resultado SHALL incluir a célula/tile/endereço, o `screen_rect` 8×8 e o scroll usado. Para
BG text; affine/extended/3D SHALL retornar erro claro. `video_state` SHALL incluir o scroll
(`hofs`/`vofs`) por BG.

#### Scenario: Célula com scroll zero
- **WHEN** o agente consulta um pixel da tela e o BG não tem scroll
- **THEN** a célula retornada corresponde ao pixel direto no mapa

#### Scenario: Célula com scroll
- **WHEN** o `BGxHOFS/VOFS` é diferente de zero
- **THEN** a célula é deslocada pelo scroll e o resultado informa `hofs`/`vofs`

#### Scenario: Wrap
- **WHEN** o pixel + scroll ultrapassa a largura/altura do mapa
- **THEN** a célula dá a volta no mapa

#### Scenario: BG affine
- **WHEN** o BG é affine
- **THEN** a tool retorna erro explicando que affine/rotation ainda não é suportado

#### Scenario: Coordenada inválida
- **WHEN** `x`/`y` estão fora de 0..255/0..191
- **THEN** a tool retorna erro claro

### Requirement: Destaque da célula no render_layer

`render_layer(engine, layer, ..., highlight=[x, y])` SHALL desenhar um retângulo 8×8 na célula
da tela indicada e devolver os metadados da célula. O destaque SHALL ser suportado apenas para
`layer=bg0..bg3`, SHALL exigir o debugger conectado e SHALL falhar com hint quando a tela do
engine não estiver incluída em `screens`.

#### Scenario: Destaque de célula
- **WHEN** o agente pede `render_layer` com `highlight`
- **THEN** o PNG inclui o retângulo na célula e a resposta traz `cell`/`screen`

#### Scenario: Sem debugger
- **WHEN** não há gdb conectado
- **THEN** a tool retorna erro + hint para conectar/parar o alvo

#### Scenario: Tela ausente
- **WHEN** `screens` não inclui a tela do engine
- **THEN** a tool retorna erro + hint

#### Scenario: Camada não-BG
- **WHEN** `layer` é `obj` ou `3d`
- **THEN** a tool retorna erro explicando que o destaque é só para BG
