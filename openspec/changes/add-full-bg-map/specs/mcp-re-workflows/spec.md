## ADDED Requirements

### Requirement: Mapa BG completo

O MCP SHALL oferecer `dump_tilemap(engine, bg)` e `render_bg_map(engine, bg)` para o mapa BG
virtual inteiro (não só a janela 256×192). `dump_tilemap` SHALL gravar em `/out` um JSON com
as células (`cell_x/y`, `entry`, `tile_index`, `tile_addr`, `palette`, `flip_h/v`, `bpp`) e
devolver caminho + dimensões/contagem. `render_bg_map` SHALL compor o mapa inteiro em PNG
(4/8bpp, flips, paleta BG) e devolver caminho + metadados. Text e affine SHALL ser suportados;
extended/bitmap/3D SHALL retornar erro claro. As leituras de mapa/tiles/paleta SHALL ser em
bulk (não uma por célula).

#### Scenario: Dump text
- **WHEN** o agente pede `dump_tilemap` de um BG text 512×512
- **THEN** recebe um JSON com as 4096 células e metadados do mapa

#### Scenario: Dump affine
- **WHEN** o agente pede `dump_tilemap` de um BG affine
- **THEN** recebe as células do mapa plano (entry de 8 bits, tile de 8bpp)

#### Scenario: Render text
- **WHEN** o agente pede `render_bg_map` de um BG text
- **THEN** recebe um PNG do mapa inteiro com paleta/flips aplicados

#### Scenario: Render affine
- **WHEN** o agente pede `render_bg_map` de um BG affine
- **THEN** recebe o mapa plano em 8bpp (sem a transformação de tela)

#### Scenario: Transparência
- **WHEN** um pixel do tile tem índice 0
- **THEN** ele sai transparente (alpha 0) no PNG

#### Scenario: BG não suportado
- **WHEN** o BG é extended/bitmap/3D
- **THEN** a tool retorna erro com hint

#### Scenario: Janela visível
- **WHEN** o mapa text é recortado no scroll atual (256×192)
- **THEN** o recorte confere com `render_layer` para a mesma camada
