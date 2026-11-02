## 1. Contrato

- [x] 1.1 `domain/contract.py` (`ArgSpec`, `Contract`, `ReturnHit`, `ContractHit`) e refactor
  de `application/args.py` para usar o contrato. Verificar: testes de domínio.
- [x] 1.2 `application/contract.py` (`ContractChecks`) com captura opcional de retorno via
  breakpoint em `lr`. Verificar: fake debugger (args, retorno, timeout).
- [x] 1.3 Tool `contract_check` com `hits`/`divergences`. Verificar: testes de tool.

## 2. Diff de patch

- [x] 2.1 `domain/patch.py` (`PatchWrite`, `Patch`, `PatchByteDiff`, `PatchDiff`) com
  aplicação/merge de faixas e comparação byte a byte.
- [x] 2.2 `application/patches.py` lendo a memória atual e a tool `diff_patch`.
  Verificar: patches iguais, divergentes, sobrepostos e inválidos.

## 3. Validação

- [x] 3.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-contract-diff --strict` verdes.
- [ ] 3.2 Smoke real opcional: contrato de um callsite conhecido e diff de um patch de teste.
