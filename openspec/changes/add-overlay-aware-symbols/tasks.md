## 1. Domínio

- [x] 1.1 `SymbolTable.add` passa a usar a chave `(addr, overlay)` e `(name, overlay)`; adicionar
  `candidates(addr, overlay=None)`, `resolve(addr, overlay=None)`, `all(overlay=None)` e
  `replace_overlay(overlay, table)`. Verificar: dois símbolos no mesmo endereço em overlays 22/25
  coexistem; `resolve` com filtro devolve o da overlay; sem filtro e ambíguo devolve `None`.
- [x] 1.2 Garantir que `from_json`/`to_json` preservam múltiplos símbolos no mesmo endereço. Verificar:
  round-trip com 22/25 no mesmo `addr` mantém os dois.

## 2. Bridge e tools de símbolo

- [x] 2.1 Adicionar `Bridge.active_overlay(core="arm9")` sem abrir o control channel (usa o
  `OverlayResolver` cacheado). Verificar: sem selection → `None`; após `overlay_select(25)` → 25.
- [x] 2.2 `symbol_lookup(addr, overlay=None)`: usa explícito > ativo; retorna símbolo único ou
  `{ambiguous: true, symbols: [...]}`. Verificar: 22/25 no mesmo endereço sem seleção → ambíguo; com
  `overlay=25` → nome da 25.
- [x] 2.3 `symbol_list(kind=None, overlay=None)`: filtro por overlay. Verificar: lista da 25 não inclui
  a 22; sem filtro inclui ambas.
- [x] 2.4 `symbol_load(path, merge=True, overlay=None)`: marca o `.map`; `merge=false` + overlay
  substitui só aquela overlay. Verificar: carregar mapa da 25 preserva o símbolo da 22 e o global.
- [x] 2.5 Atualizar docstring de `symbol_define` (overlay deixa de ser só metadado).

## 3. Anotações

- [x] 3.1 `disassemble(..., overlay=None)` anota instrução/alvo com a overlay explícita ou ativa.
  Verificar: mesmo endereço em 22/25 anota o nome correto.
- [x] 3.2 `debug_backtrace`, `find_writer`/`find_reader`, `hit_log_read`, `dma_source`,
  `args_on_hit` e `contract_check` usam `Bridge.active_overlay`; se ambíguo, símbolo `null`.
  Verificar: com `overlay_select(25)`, anotam o nome da 25; sem seleção, não inventam nome.
- [x] 3.3 `addr_valid` anota cada candidato com o símbolo daquele overlay e o topo com a seleção
  explícita/ativa. Verificar: candidato 22 → nome 22; candidato 25 → nome 25.

## 4. Docs e validação

- [x] 4.1 Atualizar a skill e a doc de decomp para a chave `(addr, overlay)`, precedência, `.map` por
  unidade e o caso ambíguo. Verificar: exemplos com 22/25 e `symbol_load(overlay=25)`.
- [x] 4.2 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-overlay-aware-symbols --strict` verdes.
- [x] 4.3 Smoke real com `xpa-khe.nds`: definir `fn_22`/`fn_25` no mesmo endereço, selecionar 25,
  consultar/disasm/anotar; e recarregar mapa da 25 sem apagar a 22.
  Verificar: nomes corretos por overlay; ambiguidade sem seleção.

### Smoke real (2026-11-02)

- `fn_22` (overlay 22) e `fn_25` (overlay 25) no mesmo `0x020A11C4`: coexistem.
- `symbol_lookup` sem filtro → `ambiguous=true` + lista; `overlay=25` → `fn_25`; com
  `overlay_select(25)` → `fn_25`.
- `addr_valid` anota cada candidato (`fn_22`/`fn_25`) e o topo usa a ativa.
- `disassemble` anota `fn_25` com a ativa.
- `symbol_load(overlay=25)` mescla; `merge=false, overlay=25` substitui só a 25 e preserva a 22.
