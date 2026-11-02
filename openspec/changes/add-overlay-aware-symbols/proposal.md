## Why

A1/A2 resolveram a ambiguidade de **overlay** (22/25 na mesma base, candidatos e seleção ativa), mas a
tabela de símbolos continua indexada **só por endereço**:

- `symbol_define(..., overlay=N)` grava `overlay` apenas como metadado.
- `symbol_lookup(addr)` e `symbol_load(path)` ignoram overlay.
- `SymbolTable.add` remove o mesmo endereço/nome **em qualquer overlay**, então um símbolo da 25 apaga o
  da 22 no mesmo endereço.
- As anotações (`disassemble`, `backtrace`, `find_writer`/`find_reader`, `hit_log_read`, `addr_valid`)
  podem mostrar o nome da overlay errada.

A3 fecha a Frente A: o símbolo passa a ser resolvido pela chave **(endereço, overlay)**, usando a mesma
seleção ativa de A1/A2, sem escolher um nome silenciosamente quando houver ambiguidade.

## What Changes

- **Domínio:** `SymbolTable` passa a indexar por `(addr, overlay)`; `resolve(addr, overlay=None)` e
  `candidates(addr, overlay=None)`; precedência explícita > overlay ativa > específico > global; `add`
  substitui apenas `(addr, overlay)`/`(name, overlay)`; `replace_overlay` para recarregar um mapa.
- **Tools:** `symbol_lookup(addr, overlay=None)`, `symbol_list(kind=None, overlay=None)`,
  `symbol_define` com overlay efetivo e `symbol_load(path, merge=True, overlay=None)` marcando o `.map`.
  Sem overlay explícito, usam a overlay ativa (`overlay_select`); se ainda houver mais de um símbolo no
  mesmo endereço, retornam `ambiguous=true` + lista, não o primeiro.
- **Anotações:** `disassemble` (com `overlay=` opcional), `backtrace`, `find_writer`/`find_reader`,
  `hit_log_read`, `dma_source`, `args_on_hit`, `contract_check` e `addr_valid` usam a overlay
  ativa/filtro; `addr_valid` anota cada candidato com o símbolo daquele overlay.
- **Compatibilidade:** símbolos antigos (`overlay=null`) continuam globais e servem de fallback.
  `symbols.json` não muda de formato.
- **Sem mudança no emulador.**

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities

- `mcp-re-workflows`: símbolos cientes de overlay (definir, listar, consultar, carregar `.map`).
- `mcp-debug-tools`: anotações de disasm/backtrace/hits/watchpoints usando a overlay ativa.

## Impact

- MCP: `domain/symbols.py`, `bridge.py`, `tools/re.py`, `tools/debug.py`, `tools/cart.py`, testes.
- Emulador: **nenhuma mudança**.
- Docs/skill: documentar a chave `(addr, overlay)`, a precedência e o fluxo `symbol_load(overlay=)`.
