## 1. Emulador

- [x] 1.1 Estender `GdbStub::HitRecord` com `pc_fault`, `width`, `rmw`; ajustar
  `RecordHit` e `CheckWatchpt(addr, kind, width, pc_fault, ...)`.
  Verificar: build do emulador sem erros.
- [x] 1.2 Em `ARM.cpp`, passar `pc_fault` (`R[15] - (thumb ? 2 : 4)`) e a largura
  (1/2/4) de `DataRead*`/`DataWrite*`; ajustar a assinatura/stub sem GDB.
  Verificar: build e smoke de um `str`/`swpb`.
- [x] 1.3 Em `CheckDmaWatchpt`, registrar `addr` (destino real), `len` e `pc` como
  `pc_fault`; incluir os campos no JSON de `gdb.hits.read`.
  Verificar: leitura do log mostra `width=len` e destino correto.

## 2. MCP

- [x] 2.1 `_hit_list` lê `pc_fault`/`width`/`rmw` com fallback para payload antigo
  (`pc_fault=pc`, `width=0`, `rmw=false`) e formata `fault_pc_symbol`/`access_addr`.
  Verificar: teste com payload novo e antigo.
- [x] 2.2 Derivar `rmw` por par read+write no mesmo `pc_fault`+`access_addr`.
  Verificar: teste com `swpb` simulado e com read/write em PCs diferentes.
- [x] 2.3 Atualizar docstring de `hit_log_read` e a skill.
  Verificar: docs citam `pc_fault`/`width`/`rmw`.

## 3. Validação

- [x] 3.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports`,
  build do emulador e `openspec validate add-hit-log-exact-access --strict`.
- [ ] 3.2 Smoke real com `xpa-khe.nds`: hit log em um store conhecido e em `swpb`
  (LZ), conferindo `pc_fault`, `access_addr`, `width`, `rmw`.
  - Parcial em 2026-11-02: campos `pc_fault`/`width`/`rmw` validados com hits de
    **breakpoint** no emulador novo; store CPU/`swpb` não reproduzido (jogo em
    loop de WFI/idle). DMA watchpoint também não disparou nesse estado.
