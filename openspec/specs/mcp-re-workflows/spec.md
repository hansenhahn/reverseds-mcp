# mcp-re-workflows Specification

## Purpose

Workflows de engenharia reversa assistida que combinam controle, depuração,
símbolos e NitroFS para responder às perguntas típicas de RE.

## Requirements

### Requirement: Achar quem escreve num endereço

O MCP SHALL oferecer um workflow que, dado um endereço, encontre o código que o
escreve (watchpoint de escrita + execução + relatório do PC e contexto).

#### Scenario: find_writer
- **WHEN** o agente pede para achar quem escreve em `0xADDR`
- **THEN** o MCP arma um watchpoint de escrita, roda e retorna o PC (e contexto) no momento da escrita

### Requirement: Achar quem lê um dado

O MCP SHALL oferecer um workflow para encontrar o código que lê um dado,
combinando watchpoints de leitura e/ou o trace de cartucho.

#### Scenario: find_reader de endereço
- **WHEN** o agente pede para achar quem lê `0xADDR`
- **THEN** o MCP arma um watchpoint de leitura, roda e retorna o PC no momento da leitura

#### Scenario: find_reader de arquivo
- **WHEN** o agente pergunta quem lê um arquivo (via NitroFS) da ROM
- **THEN** o MCP correlaciona as leituras do trace com o arquivo e aponta os acessos

### Requirement: Diferença de estado

O MCP SHALL permitir comparar estados (savestate ou regiões de memória) e destacar
o que mudou entre dois pontos.

#### Scenario: diff de memória
- **WHEN** o agente salva o estado, avança e compara
- **THEN** o MCP retorna as regiões/endereços que mudaram

### Requirement: Símbolos

O MCP SHALL permitir carregar um mapa de símbolos (`.map`) e resolver
endereço ↔ nome.

#### Scenario: Resolver endereço
- **WHEN** o agente consulta um endereço e há símbolo carregado
- **THEN** o MCP retorna o nome correspondente

### Requirement: Tradução das leituras do cartucho em arquivos (FAT/FNT)

O MCP SHALL parsear o **FNT/FAT** (NitroFS) da ROM e traduzir as leituras do
cartucho (offsets) em **arquivos** — a função central. SHALL permitir traduzir um
offset isolado e SHALL poder agregar leituras por arquivo.

#### Scenario: Offset para arquivo
- **WHEN** o agente informa um offset lido do cartucho
- **THEN** o MCP retorna o caminho do arquivo dentro da ROM

#### Scenario: Agregar leituras por arquivo
- **WHEN** o trace de cartucho acumula leituras
- **THEN** o MCP agrupa as leituras pelos arquivos correspondentes
