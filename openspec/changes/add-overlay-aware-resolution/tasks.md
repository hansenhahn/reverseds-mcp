## 1. Modelo de domínio

- [x] 1.1 Estender `Overlay` com `sinit_start`, `sinit_end`, `flags` e `compressed_size`;
  adicionar `OverlayDetails` (y9 + FAT + compressão + `code_base`/`prefix_size` opcionais) e
  `OverlayHit.offset_file`/`offset_code` (com `offset` como alias de `offset_file`).
  Verificar: testes de `OverlayTable.from_bytes` (sinit/flags) e de `OverlayHit` (offset
  file/code) verdes.
- [x] 1.2 Adicionar `OverlayTable.candidates(addr)` devolvendo todos os hits; manter
  `for_address` como primeiro hit para compatibilidade. Verificar: teste com dois overlays na
  mesma base → `len(candidates)==2` e `for_address` devolve o primeiro.

## 2. Adaptador (ROM/FAT)

- [x] 2.1 Parsear `sinit_start/end` e `flags` no `OverlayTable.from_bytes`; adicionar
  `NdsFs.span_by_id(file_id)` para obter `file_offset`/`file_size` do FAT.
  Verificar: teste sintético de y9 com sinit/flags e FAT com file id conhecido.
- [x] 2.2 Implementar `ChannelRom.overlay_details(index, core)` e
  `ChannelRom.overlay_candidates(addr, core)`; derivar `compressed` por `file_size <
  ram_size` (fallback `compressed_size` do y9), preservando `flags` cru.
  Verificar: teste com overlay comprimido (file_size < ram_size) e não comprimido
  (file_size == ram_size); `file_offset` bate com o FAT.

## 3. Resolver e seleção

- [x] 3.1 Criar `application/overlays.py` (`OverlayResolver`) com `select`, `clear`,
  `candidates`, `details` e `resolve`; seleção em memória, `code_base` validada no intervalo
  `[ram_address, ram_address + ram_size)`. Verificar: testes de seleção explícita > ativa >
  único candidato; ambíguo sem seleção → `overlay=null`.
- [x] 3.2 Expor `Bridge.overlay_resolver()` e usar o resolver nas tools.
  Verificar: `lint-imports` mantém `domain`/`application`/`infra` sem dependências proibidas.

## 4. Tools

- [x] 4.1 `overlay_details(index, core="arm9", code_base=None)` com y9 + FAT + compressão +
  `code_base`/`prefix_size`. Verificar: teste de fake bridge com overlay comprimido e
  `code_base` explícito.
- [x] 4.2 `overlay_for_address(addr, core="arm9", overlay=None, code_base=None)` devolvendo
  `overlays`, `ambiguous`, `overlay`, `offset_file`, `offset_code` (e `offset` compatível).
  Verificar: endereço na base compartilhada → dois candidatos; `overlay=25` filtra; sem
  `code_base` → `offset_code=null`.
- [x] 4.3 `overlay_select(index=None, core="arm9", code_base=None)` e estado na sessão.
  Verificar: após `overlay_select(25)`, `overlay_for_address`/`rom_details`/`addr_valid`
  escolhem 25; `overlay_select(None)` limpa.
- [x] 4.4 `rom_details(overlay=None, code_base=None)`: `runtime` inclui `overlays` e
  `ambiguous`; `overlay` é `null` quando ambíguo sem seleção. Verificar: fake debugger com PC
  na base compartilhada.
- [x] 4.5 `addr_valid(value, overlay=None, code_base=None)`: inclui `overlays`, `ambiguous`
  e offsets por candidato, mantendo `overlay`/`offset` compatíveis. Verificar: teste de
  endereço em base compartilhada e de endereço fora de overlay.

## 5. Docs e validação

- [x] 5.1 Atualizar a skill (`reverse-engineering-ds`) e a doc de decomp do projeto para
  `overlays`/`ambiguous`, `offset_file` × `offset_code`, seleção ativa e `overlay_details`;
  sem endereços fixos de jogo.
  Verificar: skill cita os dois offsets e a regra de não confiar no primeiro match.
- [x] 5.2 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-overlay-aware-resolution --strict` verdes.
- [x] 5.3 Smoke real: `overlay_for_address`/`rom_details`/`addr_valid` no caso 22/25; e
  `overlay_details`/`addr_valid` com `code_base=0x0204D0C0` no caso de prefixo `0x600`.
  Verificar: sem primeiro-match errado; `offset_file` e `offset_code` conferem com o arquivo.
  - Validado em 2026-11-02 com `xpa-khe.nds`: `0x020A11C4` → 22/25 ambíguo;
    `overlay_select(25)` escolhe 25; `overlay_details(0, code_base=0x0204D0C0)` →
    `prefix_size=0x600`; `addr_valid(0x020500D0)` → `offset_file=0x3610`,
    `offset_code=0x3010`; `rom_details` com PC no overlay → `overlays` + `ambiguous`.
