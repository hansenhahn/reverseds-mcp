## Purpose

Decodifica, de forma determinística, os registradores mapeados em IO do NDS a partir
de um schema derivado do GBATEK, para que o agente leia estados nomeados em vez de
interpretar valores hex crus.

## ADDED Requirements

### Requirement: Schema determinístico do IO map

O MCP SHALL manter um schema versionado `endereço → registrador → bitfields/enums`
derivado do GBATEK, cobrindo o escopo inicial: vídeo 2D/OAM/paletas, `VRAMCNT`/`WRAMCNT`,
`DMA`, `POWCNT1` e `DISP3DCNT`. A decodificação SHALL ser feita a partir desse schema, e
NÃO SHALL exigir interpretação em tempo de execução.

#### Scenario: Registrar um endereço
- **WHEN** um valor é lido de um endereço presente no schema
- **THEN** o decode devolve os campos nomeados (bitfields/enums) correspondentes

#### Scenario: Endereço fora do escopo
- **WHEN** o endereço não está coberto pelo schema
- **THEN** o MCP reporta que aquele endereço não é decodificável (sem inventar campos)

### Requirement: Decodificação pura

O MCP SHALL expor uma função pura `decode_io(addr, bytes)` que, a partir do schema,
devolve os campos decodificados sem realizar I/O nem depender do emulador.

#### Scenario: Decodificar sem emulador
- **WHEN** a função recebe um endereço e bytes conhecidos (ex.: `DISPCNT = 0x4001111D`)
- **THEN** devolve o decode correto, sem acessar o emulador

### Requirement: Leitura de IO decodificada

O MCP SHALL expor uma tool `io_read(addr)` que lê a memória de IO pelo debugger e devolve
os campos decodificados, exigindo o alvo **parado** e reportando erro claro quando o
endereço não é IO ou o alvo está em execução.

#### Scenario: Ler um registrador
- **WHEN** o agente chama `io_read` num endereço de IO com o alvo parado
- **THEN** recebe o valor bruto e os campos decodificados

#### Scenario: Alvo em execução
- **WHEN** o agente chama `io_read` com o alvo em execução
- **THEN** o MCP retorna erro com hint para parar/interromper antes
