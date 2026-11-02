## Why

O `io_read` só decodifica DISPCNT/BGxCNT/MASTER_BRIGHT/DISP3DCNT, POWCNT1, VRAMCNT e DMA.
Faltam os registradores que explicam **scroll, janelas, mosaic e blending** — justamente os
que a UI usa e que hoje só aparecem como hex (ou como “endereço não mapeado no schema”).

O `LIMITACOES.md` §3 registrou a lacuna na engine B (`0x04001010+`). Vários desses
registradores são **write-only** no hardware; a leitura pode voltar 0, então o schema
precisa expor essa condição em vez de fingir um decode útil.

## What Changes

- Adicionar ao schema, para **engine A e B**:
  - scroll: `BG0-3HOFS/VOFS`;
  - janelas: `WIN0/1H`, `WIN0/1V`, `WININ`, `WINOUT`;
  - `MOSAIC`;
  - blending: `BLDCNT`, `BLDALPHA`, `BLDY`.
- Marcar os registradores **write-only** e incluir `write_only` no decode; `io_read` SHALL
  avisar quando o registro é write-only (leitura pode ser 0).
- Adicionar `io_read(addr, raw=...)` para decodificar um valor conhecido **sem I/O** (útil
  para write-only e para valores extraídos de savestate/log).
- Sem mudança no emulador.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-io-decode`: schema 2D completo (scroll/janela/mosaic/blend) + metadado write-only +
  decode puro por valor.

## Impact

- MCP: `domain/io/decode.py` (`write_only`), `domain/io/registers/video.py`, `application/io.py`,
  `tools/io.py`, `tools/app.py` (`reg_dict`), testes.
- Emulador: **nenhuma mudança**.
