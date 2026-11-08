## ADDED Requirements

### Requirement: Origem da textura

O MCP SHALL oferecer `gpu3d_texture_source(index | tex_param/tex_palette)` que lê
os **bytes crus** da textura via `3d.texture_raw`, busca o **mesmo padrão na RAM**
e devolve os buffers candidatos (`candidates`, `count`, `digest`, `unknown`). Com
`dump_source=true` SHALL salvar o(s) buffer(s) candidato(s) como `.bin` em `/out`.
Sem candidato, SHALL retornar `unknown=true`, nunca uma origem inventada.

#### Scenario: Buffer de origem
- **WHEN** o agente pede a origem de uma textura
- **THEN** recebe os endereços de RAM cujos bytes batem com a textura

#### Scenario: Dump dos candidatos
- **WHEN** o agente pede `dump_source=true`
- **THEN** recebe os `.bin` dos buffers candidatos em `/out`

#### Scenario: Origem desconhecida
- **WHEN** nenhum buffer na faixa contém os bytes da textura
- **THEN** a tool responde `unknown=true` com `count=0`

### Requirement: Origem do display list

O MCP SHALL oferecer `gxfifo_source(...)` que devolve o `src`/`pc`/`frame` do
buffer que alimenta o GXFIFO e, opcionalmente, dumpar esse buffer em `/out`.

#### Scenario: Buffer do display list
- **WHEN** o agente pede a origem do GXFIFO
- **THEN** recebe o `src` e pode dumpá-lo para inspeção

### Requirement: Decode tipado do trace GXFIFO

`gxfifo_trace_read` SHALL aceitar `decode="typed"` e decodificar os parâmetros por
comando em campos semânticos: `vtx_*` → x/y/z, `texcoord` → u/v, `mtx_*` →
modo/elementos, `begin_vtxs` → primitiva. O formato cru SHALL continuar disponível
(default).

#### Scenario: Reconstruir geometria
- **WHEN** o agente lê o trace em modo tipado
- **THEN** consegue reconstruir a sequência de vértices/texcoords do frame

### Requirement: Busca de buffer na RAM

O MCP SHALL oferecer `find_bytes_in_ram(hex | from_addr/size, ram_start,
ram_size, max_hits)` para localizar na RAM um padrão (ex.: o conteúdo que foi para
VRAM/GXFIFO), com limite de tamanho e blocos.

#### Scenario: Achar o buffer de origem
- **WHEN** o agente busca um padrão extraído da VRAM na RAM
- **THEN** recebe os endereços onde ele ocorre (até `max_hits`)
