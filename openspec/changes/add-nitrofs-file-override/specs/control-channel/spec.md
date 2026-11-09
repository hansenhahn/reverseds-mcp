## ADDED Requirements

### Requirement: Controle de overrides de leitura do cartucho

O canal de controle SHALL expor métodos para administrar overrides de conteúdo do cartucho:
`cart.override.set`, `cart.override.clear`, `cart.override.list`, `cart.override.reload` e
`cart.override.stats`.

- `cart.override.set` SHALL receber `start`, `end` e `host_path`, validar o range contra o
  tamanho da ROM carregada, rejeitar sobreposição com override existente e ler o arquivo do
  host.
- `cart.override.list` SHALL devolver, por override, `start`, `end`, `host_path`, `host_size`,
  `loaded` e os contadores de leitura.
- `cart.override.reload` SHALL reler o arquivo do host e publicar o novo conteúdo.
- `cart.override.stats` SHALL devolver os contadores de leitura do override do range.
- `cart.override.clear` SHALL remover o override do range.

#### Scenario: Registrar override
- **WHEN** o agente chama `cart.override.set` com um range válido e um arquivo do host existente
- **THEN** o override passa a ser servido nas leituras do cartucho dentro do range

#### Scenario: Listar overrides
- **WHEN** o agente chama `cart.override.list`
- **THEN** recebe os ranges registrados com caminho do host, tamanho e estado de carga

#### Scenario: Sobreposição de ranges
- **WHEN** o agente registra um range que se sobrepõe a um override existente
- **THEN** o servidor responde com erro explícito, sem alterar os overrides já registrados

#### Scenario: Range fora da ROM
- **WHEN** o agente registra um range com `end` maior que o tamanho da ROM carregada
- **THEN** o servidor responde com erro explícito

#### Scenario: Arquivo do host ausente
- **WHEN** o agente registra ou recarrega um `host_path` que não existe
- **THEN** o servidor responde com erro explícito, sem derrubar a conexão

#### Scenario: Recarregar override
- **WHEN** o agente chama `cart.override.reload` para um range registrado
- **THEN** o servidor relê o arquivo do host e o novo conteúdo passa a ser servido

#### Scenario: Contadores de leitura
- **WHEN** o agente chama `cart.override.stats` após o jogo ler o range
- **THEN** recebe a contagem de leituras e de bytes servidos pelo override

#### Scenario: Remover override
- **WHEN** o agente chama `cart.override.clear` para um range registrado
- **THEN** as leituras passam a vir da ROM original

#### Scenario: Sem cartucho
- **WHEN** o agente chama qualquer `cart.override.*` sem cartucho carregado
- **THEN** o servidor responde com erro explícito

### Requirement: Carga mínima na thread de emulação (overrides)

A leitura do arquivo do host e a serialização JSON dos métodos `cart.override.*` SHALL ocorrer
na thread que atende o cliente, fora da thread de emulação. A thread de emulação SHALL apenas
comparar o offset lido com os ranges ativos, sem I/O e sem alocação por acesso.

#### Scenario: I/O fora da thread de emulação
- **WHEN** o agente chama `cart.override.set` ou `cart.override.reload`
- **THEN** a leitura do arquivo do host ocorre fora da thread de emulação

#### Scenario: Custo por leitura sem override
- **WHEN** nenhum override está ativo e o jogo lê o cartucho
- **THEN** o caminho de leitura executa somente uma verificação atômica de flag
