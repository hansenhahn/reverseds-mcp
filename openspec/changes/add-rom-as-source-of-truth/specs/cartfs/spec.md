## MODIFIED Requirements

### Requirement: Interpretação nativa do filesystem

O sistema SHALL interpretar o filesystem do cartucho lendo o header da ROM carregada
**no emulador** (via canal de controle) e parseando `FNT`/`FAT` diretamente, sem depender de
ferramenta externa (como o `ndstool`) nem de um caminho de arquivo/bind-mount. Quando a ROM
carregada mudar, o sistema SHALL remontar o filesystem a partir da nova ROM.

#### Scenario: ROM com NitroFS
- **WHEN** a ROM é carregada no emulador e o agente usa uma tool de cartucho
- **THEN** o FS é interpretado a partir do header da ROM em execução, com a árvore de
  diretórios e a contagem de arquivos

#### Scenario: Sem caminho de arquivo
- **WHEN** o MCP roda sem `RE_MCP_ROM` e sem a ROM montada no contêiner
- **THEN** a listagem, o mapeamento offset→arquivo e a leitura continuam funcionando com a
  ROM servida pelo emulador

#### Scenario: Troca de ROM
- **WHEN** outra ROM é carregada no emulador entre duas operações do MCP
- **THEN** a operação seguinte usa o filesystem da nova ROM, sem reiniciar o MCP

#### Scenario: Sem ferramenta externa
- **WHEN** o MCP roda em um ambiente sem o `ndstool`
- **THEN** a listagem e o mapeamento offset→arquivo continuam funcionando
