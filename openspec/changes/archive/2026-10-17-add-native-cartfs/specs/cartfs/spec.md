## Purpose

Interpreta nativamente o filesystem do cartucho (header NDS + FAT + FNT), sem ferramenta
externa, expondo a árvore de arquivos, o mapeamento offset→arquivo e o conteúdo.

## ADDED Requirements

### Requirement: Interpretação nativa do filesystem

O sistema SHALL interpretar o filesystem do cartucho lendo o header da ROM (offsets de
`FNT`/`FAT`) e parseando `FNT`/`FAT` diretamente, sem depender de ferramenta externa
(como o `ndstool`).

#### Scenario: ROM com NitroFS
- **WHEN** a ROM é aberta
- **THEN** o FS é interpretado a partir do header, com a árvore de diretórios e a contagem de arquivos

#### Scenario: Sem ferramenta externa
- **WHEN** o MCP roda em um ambiente sem o `ndstool`
- **THEN** a listagem e o mapeamento offset→arquivo continuam funcionando

### Requirement: Árvore de arquivos

O sistema SHALL permitir listar os arquivos do FS com seus caminhos e ids.

#### Scenario: Listar arquivos
- **WHEN** o agente pede a lista de arquivos
- **THEN** recebe os caminhos (ex.: `/data/sound_data.sdat`) e os respectivos ids

### Requirement: Offset para arquivo

O sistema SHALL mapear um offset da ROM para o arquivo que o contém.

#### Scenario: Offset dentro de um arquivo
- **WHEN** o agente informa um offset da ROM
- **THEN** o sistema devolve o caminho do arquivo (ou nada, se não pertencer a nenhum)

### Requirement: Conteúdo de arquivo

O sistema SHALL permitir ler o conteúdo de um arquivo do FS por caminho ou id.

#### Scenario: Ler um arquivo
- **WHEN** o agente pede o conteúdo de um arquivo
- **THEN** o sistema devolve os bytes do arquivo
