## Why

Para entender o código que lê/escreve um dado (ex.: o montador do HUD que achamos), o
agente hoje precisa ler bytes via memória e **desmontar fora do MCP** (capstone externo),
quebrando o loop de RE dentro do servidor.

Este change adiciona uma tool de **desassemblagem** (ARM/Thumb) que lê a memória e devolve
as instruções, integrando com `symbol_lookup` para nomear saltos.

## What Changes

- Nova tool `disassemble(addr, count, mode)` que lê `count` instruções a partir de `addr`
  no core conectado e devolve `[{address, bytes, mnemonic, op_str}]`.
- `mode`: `arm` ou `thumb` (default `arm`).
- Usa **capstone** (nova dependência).
- Sem mudança no emulador.

## Capabilities

### Modified Capabilities
- `mcp-debug-tools`: adiciona desassemblagem.

## Impact

- MCP: nova dependência (`capstone`) no `pyproject`/imagem; uma função de domínio pura e uma tool.
- Lê memória pela porta `Debugger` existente (o alvo precisa estar **parado**).
