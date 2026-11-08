## ADDED Requirements

### Requirement: Bytes crus da textura

O canal SHALL expor `3d.texture_raw` (por `index` ou `tex_param`/`tex_palette`)
que devolve os **bytes crus** da textura lidos de `VRAMFlat_Texture`, com
`format_id`, `width`, `height`, `size`, servidos no frame binário. Formatos não
suportados (ex.: comprimido 4x4) SHALL retornar erro claro.

#### Scenario: Textura crua
- **WHEN** o agente pede `3d.texture_raw` de uma textura não comprimida
- **THEN** recebe os bytes crus (frame binário) e os metadados

#### Scenario: Formato não suportado
- **WHEN** a textura usa formato comprimido
- **THEN** o canal retorna erro claro, sem derrubar a emulação

### Requirement: Histórico de origem de escrita em VRAM

O canal SHALL expor `origin.start`, `origin.stop` e `origin.query` para um ring
bounded de writes que cobrem VRAM, registrando `dst_lo`, `dst_hi`, `src`, `len`,
`pc`, `frame` e `kind` (`dma`/`cpu`). O ring SHALL ser armado sob demanda, com
custo O(1) por transferência e zero custo por quadro quando desligado.
`origin.query` SHALL receber `addr`, `len`, `max_age_frames` e `max_hits`, devolver
as transferências que sobrepõem a faixa (mais recente primeiro) e SHALL responder
`unknown` (com `hint` para armar o histórico) quando nada casar.

#### Scenario: Origem encontrada
- **WHEN** o histórico está armado e um DMA escreve na VRAM de uma textura
- **THEN** `origin.query` devolve o `src`, `len`, `pc` e `frame` da transferência

#### Scenario: Histórico não armado
- **WHEN** o agente consulta uma faixa sem ter armado o histórico
- **THEN** recebe `unknown` com um `hint`, nunca uma origem inventada

#### Scenario: Ring cheio
- **WHEN** mais writes ocorrem do que a capacidade do ring
- **THEN** os mais antigos são descartados e `dropped` aumenta

### Requirement: Origem do GXFIFO / display list

O canal SHALL registrar no histórico de origem as transferências cujo destino
cobre `0x04000400` (GXFIFO) e SHALL expor `gxfifo.origin`, devolvendo `src`, `pc`,
`frame` e `len` da transferência que alimenta o GXFIFO.

#### Scenario: Display list por DMA
- **WHEN** um DMA alimenta o GXFIFO a partir de um buffer de RAM
- **THEN** `gxfifo.origin` devolve o `src`/`pc`/`frame` desse buffer

#### Scenario: Sem transferência observada
- **WHEN** não há transferência de GXFIFO no histórico
- **THEN** a consulta retorna `unknown` com dica
