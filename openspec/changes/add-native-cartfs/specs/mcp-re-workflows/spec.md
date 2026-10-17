## ADDED Requirements

### Requirement: Tools de filesystem e overlays

O MCP SHALL expor tools para listar e ler arquivos do filesystem do cartucho e para listar
overlays e resolver um endereço de RAM → overlay, sem depender de ferramenta externa.

#### Scenario: Listar arquivos do cartucho
- **WHEN** o agente pede a lista de arquivos
- **THEN** o MCP devolve os caminhos e ids do filesystem da ROM

#### Scenario: Ler um arquivo do cartucho
- **WHEN** o agente pede o conteúdo de um arquivo do FS
- **THEN** o MCP grava o arquivo no diretório de saída (`/out`) e devolve o caminho

#### Scenario: Resolver endereço para overlay
- **WHEN** o agente informa um endereço de RAM
- **THEN** o MCP devolve o overlay correspondente (ou nada)
