## ADDED Requirements

### Requirement: Estado do pipeline 3D

O canal SHALL expor `3d.state`, retornando o estado decodificado do core 3D
(read-only) de forma consistente: enable de geometria/renderização,
`DISP3DCNT`, `GXStat`, níveis de `CmdFIFO`/`CmdPIPE`/`CmdStallQueue`, matrix mode,
matrizes de projeção/posição/vetor/textura/clip, viewport, alpha, fog, toon/edge
e contadores de vértices/polígonos. A leitura SHALL usar um snapshot **one-shot do
frame completo**, tirado no VBlank/fim de frame, e SHALL NOT ler estado parcial de
meio de frame.

#### Scenario: Ler o estado 3D do frame completo
- **WHEN** o agente chama `3d.state` num frame 3D
- **THEN** recebe as matrizes, viewport, níveis de FIFO e contadores coerentes com
  o frame completo (finalizado no VBlank), sem estado de meio de frame

#### Scenario: Sem core 3D ativo
- **WHEN** o agente chama `3d.state` com a geometria/rendering desabilitados
- **THEN** o retorno indica `enabled.geometry/enabled.rendering` falsos sem erro

### Requirement: Dump de polígonos do frame

O canal SHALL expor `3d.polygons` com `max_items` (1..8192) e `vertices` (bool),
devolvendo os polígonos da lista renderizada do frame completo
(`RenderPolygonRAM`, finalizada no VBlank), com atributos e, quando pedido, os
vértices (posição final, Z/W, cor, texcoord). O dump SHALL vir do mesmo snapshot
one-shot do frame que `3d.state`.

#### Scenario: Polígonos do frame
- **WHEN** o agente chama `3d.polygons` num frame com geometria
- **THEN** recebe `count`, `total` e a lista de polígonos limitada a `max_items`,
  coerente com o frame de `3d.state`

#### Scenario: Sem vértices
- **WHEN** o agente chama com `vertices=false`
- **THEN** os polígonos vêm sem a lista de vértices

#### Scenario: Limite inválido
- **WHEN** `max_items` está fora de 1..8192
- **THEN** o canal normaliza para o limite válido (sem erro de execução)

### Requirement: Dump de texturas 3D

O canal SHALL expor `3d.textures`, listando as texturas usadas pelos polígonos do
frame (pares únicos de `TexParam`/`TexPalette`, com formato, tamanho, paleta e
endereço de VRAM) a partir do snapshot do VBlank. O canal SHALL expor
`3d.texture`, que decodifica uma textura da lista para RGBA usando o decoder
existente do renderer, servindo o resultado no frame binário. Formatos não
suportados SHALL retornar erro claro, sem derrubar a emulação.

#### Scenario: Listar texturas do frame
- **WHEN** o agente chama `3d.textures` num frame 3D
- **THEN** recebe as texturas referenciadas pelos polígonos do frame, sem duplicatas

#### Scenario: Baixar uma textura
- **WHEN** o agente pede `3d.texture` de uma textura da lista
- **THEN** recebe RGBA (frame binário) e os metadados (largura/altura/formato)

#### Scenario: Formato não suportado
- **WHEN** a textura usa um formato que o decoder não trata
- **THEN** o canal retorna erro claro e a emulação segue normalmente

### Requirement: Trace da fila GXFIFO

O canal SHALL expor `3d.gxfifo.start`, `3d.gxfifo.read` e `3d.gxfifo.stop`. Com a
trace ligada, cada entrada enfileirada no GXFIFO pelo caminho de escrita
(CPU/DMA) SHALL ser registrada em um ring buffer sem bloquear a emulação, com
`cmd`, `param`, `pc`, `frame` e a profundidade `fifo` no momento do enfileiramento.
`read` SHALL drenar os itens (mais antigos primeiro) e informar `count`/`dropped`;
além do cru, `read` SHALL decodificar o stream em comandos legíveis (`name` +
`params`, ex.: `begin_vtxs`, `mtx_restore`, `texcoord`, `vtx`, `end_vtxs`),
usando uma tabela de nomes/comprimento de parâmetros, sem decodificar na
EmuThread. `stop` SHALL desligar o registro mantendo o buffer legível. Sem a trace
ligada, não SHALL haver custo relevante por quadro.

#### Scenario: Ordem de enfileiramento
- **WHEN** a trace está ligada e o jogo enfileira comandos por alguns frames
- **THEN** `read` devolve a ordem das entradas com `pc`, `frame` e a profundidade

#### Scenario: Decode legível
- **WHEN** o agente lê a trace de uma cena 3D
- **THEN** cada comando vem com `name` e `params` legíveis (ex.: `begin_vtxs 0`,
  `texcoord u v`, `vtx x y z`) além dos campos crus

#### Scenario: Ring cheio
- **WHEN** mais entradas ocorrem do que a capacidade
- **THEN** as mais antigas são descartadas e `dropped` aumenta

#### Scenario: Parar e ler
- **WHEN** o agente chama `stop` e depois `read`
- **THEN** as entradas já coletadas continuam disponíveis

#### Scenario: Sem trace
- **WHEN** `read` é chamado sem `start`
- **THEN** retorna `count=0` e lista vazia, sem erro
