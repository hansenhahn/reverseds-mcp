## Why

Na sessão de RE do Hotel Dusk o agente teve que interpretar valores de IO crus
(`DISPCNT`, `POWCNT1`, `VRAMCNT`) e reimplementar a decodificação à mão — erro-prono
(produziu a "paleta 15 fantasma" e conclusões erradas sobre o mapeamento de VRAM). O
GBATEK documenta esses registradores de forma estável e completa; compilá-los como dados
determinísticos tira a interpretação do runtime do agente.

## What Changes

- Novo domínio **MCP** de decodificação do IO map, derivado do **GBATEK**: schema
  versionado `endereço → registrador → bitfields/enums`.
- Função pura `decode_io(addr, bytes)`.
- Tool `io_read(addr)`: lê a memória mapeada em IO pelo gdb e devolve os campos nomeados.
- Tools semânticas de vídeo: `video_state(engine)`, `vram_layout()` e `read_vram(...)`.
- **Nada muda no emulador** (MCP-only).
- Escopo inicial: vídeo (2D/OAM/paletas), `VRAMCNT`/`WRAMCNT`, `DMA`, `POWCNT1`,
  `DISP3DCNT`. Outros registradores entram depois, se houver demanda.
- Nota de verificação: o GBATEK marca `VRAMCNT` como `(W)`, mas o melonDS expõe leitura
  (confirmado por smoke test), então `vram_layout()` pode ler o mapeamento em tempo real.

## Capabilities

### New Capabilities
- `mcp-io-decode`: schema do IO map (GBATEK) + `decode_io` puro + tool `io_read`.
- `mcp-video-tools`: consultas semânticas de vídeo (`video_state`, `vram_layout`,
  `read_vram`) construídas sobre o decode.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- MCP: schema + `decode_io` puro em `domain/`; serviço que orquestra a porta `Debugger`
  em `application/`; tools finas em `tools/`. Sem porta nova e sem dependência nova
  (schema embutido/vendorizado).
- Não toca o emulador.
- Sem custo por quadro (tudo sob demanda, fora da EmuThread).
