## ADDED Requirements

### Requirement: ROM em execução como fonte da verdade

O MCP SHALL usar a ROM carregada no emulador como fonte da verdade para o NitroFS e os
overlays. O MCP SHALL expor `rom_info` com a identidade da ROM em execução e SHALL indicar
quando não há ROM carregada. As tools de cartucho NÃO SHALL depender de caminho de arquivo,
bind-mount ou da variável `RE_MCP_ROM`.

#### Scenario: Confirmar a ROM em uso
- **WHEN** o agente chama `rom_info`
- **THEN** recebe nome, tamanho, gamecode e checksum da ROM carregada no emulador

#### Scenario: Sem ROM
- **WHEN** o agente chama `rom_info` sem cartucho carregado
- **THEN** recebe `loaded: false`, sem erro

#### Scenario: Tools de cartucho sem configuração de ROM
- **WHEN** o agente chama `cart_list`/`cart_file`/`overlay_list` apenas com o emulador rodando
- **THEN** as tools usam a ROM carregada, sem `RE_MCP_ROM`
