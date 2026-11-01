## Why

`rom_info` dá a identidade, mas os detalhes de proveniência (header completo, ARM9/ARM7,
FNT/FAT, tabelas y9) ficam espalhados e o overlay atual só aparece se o agente cruzar PC com
`overlay_for_address`. Isso custa chamadas e favorece a confusão “build/overlay errado”. Uma
única chamada `rom_details` resolve identidade + header + derivados + overlay do PC.

## What Changes

- Nova tool **`rom_details`** lendo a ROM **em execução**: identidade (`rom_info`), header
  completo (GBATEK “DS Cartridge Header”), contagem de arquivos NitroFS, contagem de overlays
  ARM9/ARM7 e, se o gdb estiver conectado, `core`/`pc`/overlay atual.
- `CartFs` passa a expor o **header completo** (0x200) e `NdsHeader` parseia os campos de
  título/ARM9/ARM7/FNT/FAT/tabelas/CRCs; dados ausentes são tratados como zero.
- Read-only; **sem mudança no emulador** (usa `rom.read` já existente).

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-re-workflows`: adiciona `rom_details` (identidade + header + derivados + runtime).
- `cartfs`: expõe o header completo da ROM carregada.

## Impact

- MCP: `domain/cartfs.py` (header completo), `application/ports/cartfs.py` (`header`),
  `infra/ndsrom.py` (leitura de 0x200), `tools/cart.py` (`rom_details`), testes.
- Emulador: **nenhuma mudança**.
