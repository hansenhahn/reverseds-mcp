## ADDED Requirements

### Requirement: Célula de BG para tile

O MCP SHALL oferecer `map_cell(engine, bg, x, y)` que resolva uma célula de BG text/affine
para a entrada do mapa, índice do tile, endereço do tile, paleta/flip/bpp e char/screen base.
BG extended/bitmap/3D SHALL retornar erro claro.

#### Scenario: Célula text
- **WHEN** o agente resolve uma célula de um BG text
- **THEN** recebe entrada, tile index, tile address e paleta

#### Scenario: Célula affine
- **WHEN** o agente resolve uma célula de um BG affine
- **THEN** recebe o tile index/address (8bpp) e `palette=null`

#### Scenario: BG não suportado
- **WHEN** o BG é extended/bitmap/3D
- **THEN** a tool retorna erro explicando o suporte a text/affine

### Requirement: Bytes de tile e busca na RAM

O MCP SHALL oferecer `vram_tile_bytes(engine, tile_index, layer, bg, bpp)` para ler os bytes
de um tile BG/OBJ (4/8bpp) e `find_tile_in_ram(...)` para procurar esse padrão na RAM e
devolver os endereços encontrados.

#### Scenario: Ler tile
- **WHEN** o agente pede os bytes de um tile
- **THEN** recebe endereço, bpp, tamanho e hex

#### Scenario: Achar tile na RAM
- **WHEN** o padrão do tile existe na RAM
- **THEN** a tool devolve os endereços (até o limite)

#### Scenario: Tile ausente
- **WHEN** o padrão não existe na faixa
- **THEN** a lista vem vazia

### Requirement: Origem DMA de um endereço de VRAM

O MCP SHALL oferecer `dma_source(vram_addr, seconds, batch, timeout_ms)` que colete o trace de
DMA por uma janela e devolva os transfers cujo destino cobre `vram_addr`, com `src`, `dst`,
`length`, `cpu`, `pc` e símbolo quando houver.

#### Scenario: DMA encontrado
- **WHEN** um DMA escreve na faixa durante a janela
- **THEN** o resultado lista o transfer e o PC programador

#### Scenario: Nenhum DMA
- **WHEN** nenhum DMA escreve na faixa
- **THEN** o resultado tem `count=0` e lista vazia
