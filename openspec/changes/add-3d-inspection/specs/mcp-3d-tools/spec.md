## ADDED Requirements

### Requirement: Tools de estado, polígonos e texturas 3D

O MCP SHALL oferecer `gpu3d_state()`, `gpu3d_polygons(max_items=512,
vertices=True)`, `gpu3d_textures()` e `gpu3d_texture_dump(index)` que chamam,
respectivamente, `3d.state`, `3d.polygons`, `3d.textures` e `3d.texture` no canal
de controle. `gpu3d_texture_dump` SHALL salvar a textura como PNG em `/out`
(como `screen_capture`). Os resultados de estado/polígonos/texturas SHALL refletir
o frame completo (snapshot do VBlank). Erros do canal SHALL ser propagados com dica
quando o emulador não estiver rodando com o canal ativo.

#### Scenario: Estado 3D
- **WHEN** o agente chama `gpu3d_state`
- **THEN** recebe o estado 3D decodificado do frame completo

#### Scenario: Polígonos
- **WHEN** o agente chama `gpu3d_polygons`
- **THEN** recebe `count`, `total` e a lista de polígonos

#### Scenario: Texturas
- **WHEN** o agente chama `gpu3d_textures` e depois `gpu3d_texture_dump`
- **THEN** recebe a lista de texturas do frame e o PNG da textura escolhida em
  `/out`

#### Scenario: Emulador sem canal
- **WHEN** o canal de controle não está conectado
- **THEN** a tool devolve `{"error", "hint"?}` em vez de exceção

### Requirement: Tools de trace GXFIFO

O MCP SHALL oferecer `gxfifo_trace_start(max_items=65536)`,
`gxfifo_trace_read(seconds=0.0)` e `gxfifo_trace_stop()`. `gxfifo_trace_read`
SHALL permitir esperar `seconds` antes de drenar e SHALL devolver
`{count, dropped, commands[]}`, com cada comando contendo os campos crus
(`cmd`, `param`, `pc`, `frame`, `fifo`) e a forma decodificada (`name`,
`params`); o docstring SHALL alertar que, em FIFO alimentado por DMA, `pc` é o PC
da CPU no enfileiramento e não necessariamente o programador do DMA (parear com
`dma_trace` quando importar).

#### Scenario: Fluxo start/read/stop
- **WHEN** o agente chama start, espera e lê, e depois para
- **THEN** recebe as entradas coletadas com nomes legíveis e o `stop` não apaga o
  buffer

#### Scenario: Leitura antes do start
- **WHEN** o agente lê sem ter iniciado
- **THEN** recebe `count=0` (ou erro com dica), sem quebrar a sessão
