## 1. Modelo/porta

- [x] 1.1 Expandir `NdsHeader` para o header completo (0x200, pad com zero) e adicionar
  `CartFs.header()` + `ChannelRom.header()`. Verificar: testes de `NdsHeader.from_bytes`
  (completo e curto) e `ChannelRom` verdes.
- [x] 1.2 Adicionar `rom_details` em `tools/cart.py` com identidade/header/derivados/runtime.
  Verificar: testes com fake bridge (header, contagens, overlay, sem gdb e sem ROM).

## 2. Validação

- [x] 2.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-rom-details --strict` verdes. (147 testes no estado atual.)
- [x] 2.2 Smoke real com o emulador: `rom_info`/`rom_details` com `xpa-khe.nds`; header
  (`358/2 DAYS`, `YKGP`), 1595 arquivos, 303 overlays ARM9; com gdb, `runtime.pc=0x02003c50`
  e overlay `null`. Validado em 2026-11-01.
