## 1. args_on_hit

- [x] 1.1 Criar `application/args.py` com captura de `r0..r3`/`sp`/`lr`/`cpsr` + pilha,
  schema raso (`int`, `ptr`, `nonzero`, `zero`) e remoção do breakpoint em `finally`.
  Verificar: testes com `Debugger` fake (1 e N hits, divergência, timeout).
- [x] 1.2 Tool `args_on_hit` com anotação `pc_symbol` e descoberta. Verificar: teste de tool
  e `list_tools`.

## 2. field_xref / field_writers

- [x] 2.1 `SymbolTable.by_name` (para base por nome) + tool `field_xref`/`field_writers`
  usando `Watchpoints`, com `pc_symbol`. Verificar: testes com fake debugger/símbolos.

## 3. struct_candidate

- [x] 3.1 Criar `domain/structs.py` com scan puro de `[rN,#imm]` (larguras, registradores) e
  render C com padding. Verificar: testes de domínio com bytes ARM sintéticos.
- [x] 3.2 Tool `struct_candidate(code, size, mode)` lendo memória pelo debugger. Verificar:
  teste de tool com fake debugger.

## 4. Validação

- [x] 4.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-decomp-helpers --strict` verdes.
- [ ] 4.2 Smoke opcional com o emulador: um callsite/field real e um `struct_candidate` de
  uma função conhecida. (Sem emulador, coberto por fakes.)

> Validado em 2026-11-01: `pytest` (155), `pyright`, `lint-imports` e
> `openspec validate --strict` verdes. `args_on_hit`/`field_xref` têm testes com fakes;
> `struct_candidate` cobre scan/render de loads/stores ARM.
