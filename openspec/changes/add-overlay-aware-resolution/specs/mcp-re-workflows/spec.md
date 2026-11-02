## MODIFIED Requirements

### Requirement: Tools de filesystem e overlays

O MCP SHALL expor tools para listar e ler arquivos do filesystem do cartucho e para listar
overlays, resolver um endereço de RAM → overlays candidatos e obter detalhes de um overlay,
sem depender de ferramenta externa. `overlay_for_address` SHALL devolver todos os candidatos
(`overlays`), `ambiguous` e os offsets `offset_file`/`offset_code`, mantendo `overlay` e
`offset` para compatibilidade (sem escolher o primeiro silenciosamente quando ambíguo).
`overlay_details` SHALL expor y9 + FAT + compressão + base de código opcional.
`rom_details` SHALL usar a seleção ativa ou o único candidato; quando ambíguo e sem seleção,
`runtime.overlay` SHALL ser `null` e `runtime.ambiguous` SHALL ser verdadeiro.

#### Scenario: Listar arquivos do cartucho
- **WHEN** o agente pede a lista de arquivos
- **THEN** o MCP devolve os caminhos e ids do filesystem da ROM

#### Scenario: Ler um arquivo do cartucho
- **WHEN** o agente pede o conteúdo de um arquivo do FS
- **THEN** o MCP grava o arquivo no diretório de saída (`/out`) e devolve o caminho

#### Scenario: Resolver endereço para overlay
- **WHEN** o agente informa um endereço coberto por um único overlay
- **THEN** o MCP devolve o overlay, `offset_file` e `ambiguous=false`

#### Scenario: Resolver endereço em base compartilhada
- **WHEN** o agente informa um endereço coberto por dois overlays na mesma base
- **THEN** o MCP devolve os dois candidatos e `ambiguous=true`, sem escolher um deles
  silenciosamente

#### Scenario: Detalhes de overlay
- **WHEN** o agente pede os detalhes de um overlay
- **THEN** o MCP devolve y9 + `file_offset`/`file_size` + compressão e, se informado,
  `code_base`/`prefix_size`

#### Scenario: ROM sem overlay
- **WHEN** o endereço não pertence a nenhum overlay
- **THEN** a lista de candidatos vem vazia, sem erro

## ADDED Requirements

### Requirement: Seleção de overlay ativa

O MCP SHALL oferecer `overlay_select(index=None, core="arm9", code_base=None)` para o agente
declarar qual overlay está residente e, opcionalmente, a base de código. A seleção SHALL ser
estado de sessão (não persistido, sem mudança no emulador) e SHALL ser usada por
`overlay_for_address`, `rom_details` e `addr_valid` quando o chamador não informar um overlay
explícito. `overlay_select(None)` SHALL limpar a seleção do core.

#### Scenario: Selecionar overlay
- **WHEN** o agente seleciona a overlay 25
- **THEN** as próximas resoluções ambíguas usam a 25 como `overlay`, mantendo `overlays` com
  todos os candidatos

#### Scenario: Selecionar com base de código
- **WHEN** o agente seleciona uma overlay e informa `code_base`
- **THEN** as resoluções passam a incluir `offset_code`/`prefix_size` coerentes

#### Scenario: Limpar seleção
- **WHEN** o agente chama `overlay_select(None)`
- **THEN** a seleção do core é limpa e a ambiguidade volta a ser reportada

#### Scenario: Seleção stale
- **WHEN** o overlay é recarregado e a seleção não é refeita
- **THEN** o MCP não detecta isso automaticamente; o agente deve revalidar com
  `overlay_select`/`overlay_for_address`

### Requirement: Validação de endereço com overlay ambíguo

O MCP SHALL fazer `addr_valid` devolver, além do valor normalizado e da região, **todos** os
overlays candidatos (`overlays`), `ambiguous` e, por candidato, `offset_file` e
`offset_code` (quando a base de código for conhecida). A seleção ativa SHALL escolher o
`overlay`; sem seleção e com mais de um candidato, `overlay` SHALL ser `null` (não o primeiro
match). Um endereço fora de overlay SHALL continuar válido, com lista vazia.

#### Scenario: Endereço em base compartilhada
- **WHEN** o agente valida um endereço coberto por 22 e 25 sem seleção ativa
- **THEN** recebe `overlays` com os dois, `ambiguous=true`, `overlay=null` e `offset_file` por
  candidato

#### Scenario: Seleção ativa
- **WHEN** o agente selecionou a overlay 25 e valida um endereço da base compartilhada
- **THEN** `overlay` é a 25, sem esconder os outros candidatos

#### Scenario: Base de código conhecida
- **WHEN** há `code_base` configurada para a overlay escolhida
- **THEN** o candidato inclui `offset_code` e `prefix_size`

#### Scenario: Endereço sem overlay
- **WHEN** o endereço não pertence a nenhum overlay
- **THEN** `overlays` é vazio, `overlay=null` e o restante do `addr_valid` continua válido
