## ADDED Requirements

### Requirement: Override de arquivo NitroFS pelo agente

O MCP SHALL expor tools para substituir em runtime o conteúdo de um arquivo NitroFS por um
arquivo do host, sem repack da ROM e sem write de RAM. As tools SHALL resolver o caminho
NitroFS para o range `[rom_start, rom_end)` usando o FNT/FAT da ROM carregada e SHALL enviar o
range absoluto ao emulador. O MCP SHALL oferecer set, clear, list, reload e stats, e NÃO SHALL
engolir erros do emulador.

#### Scenario: Tool de override exposta
- **WHEN** o agente lista as tools do MCP
- **THEN** `cart_override_set`, `cart_override_clear`, `cart_override_list`,
  `cart_override_reload` e `cart_override_stats` estão disponíveis

#### Scenario: Registrar override por caminho NitroFS
- **WHEN** o agente chama `cart_override_set` com um caminho existente no NitroFS e um arquivo do host
- **THEN** o MCP resolve o range pelo FAT e registra o override no emulador, retornando
  `rom_start`, `rom_end` e `host_size`

#### Scenario: Caminho ausente no NitroFS
- **WHEN** o agente chama `cart_override_set` com um caminho que não existe no FNT/FAT
- **THEN** o MCP retorna `{"error", "hint"?}` sem chamar o emulador

#### Scenario: Erro do emulador propagado
- **WHEN** o emulador responde `host file missing` ou `overlapping override`
- **THEN** o MCP devolve o erro explícito ao agente, sem mascará-lo

#### Scenario: Conferir leitura do override
- **WHEN** o agente chama `cart_override_stats` após carregar a cena
- **THEN** recebe contadores de leitura que comprovam que o jogo leu o range sobrescrito
