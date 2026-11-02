## ADDED Requirements

### Requirement: Registradores de vídeo 2D (A/B)

O schema de IO SHALL cobrir, para as engines A e B, `BG0-3HOFS/VOFS`, `WIN0/1H/V`, `WININ`,
`WINOUT`, `MOSAIC`, `BLDCNT`, `BLDALPHA` e `BLDY`, com bitfields nomeados. Os registradores
write-only SHALL ser marcados com `write_only=true`. `io_read` SHALL reportar `write_only`
e SHALL incluir um `hint` quando `write_only` for verdadeiro e o valor lido for 0.
`io_read(addr, raw=...)` SHALL decodificar o valor informado sem acessar o emulador.

#### Scenario: Scroll
- **WHEN** o agente lê `BG0HOFS` da engine B
- **THEN** recebe `offset` decodificado (0..511)

#### Scenario: Janela
- **WHEN** o agente lê `WIN0H`/`WIN0V`/`WININ`
- **THEN** recebe `left`/`right`, `top`/`bottom` e os enables por BG/OBJ/efeito

#### Scenario: Mosaic
- **WHEN** o agente lê `MOSAIC`
- **THEN** recebe os tamanhos H/V de BG e OBJ

#### Scenario: Blending
- **WHEN** o agente lê `BLDCNT`/`BLDALPHA`/`BLDY`
- **THEN** recebe alvos, modo de efeito, EVA/EVB/EVY

#### Scenario: Write-only
- **WHEN** o registro é write-only e a leitura retorna 0
- **THEN** o resultado marca `write_only=true` e traz um `hint` explicando que a leitura
  pode ser 0

#### Scenario: Decode puro
- **WHEN** o agente chama `io_read` com `raw=...`
- **THEN** o valor é decodificado sem ler memória nem conectar no debugger

#### Scenario: Endereço não coberto
- **WHEN** o endereço não está no schema
- **THEN** o MCP continua retornando erro claro (sem inventar campos)
