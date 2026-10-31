## 1. Breakpoint condicional + comandos

- [x] 1.1 Estender a porta `Debugger.set_breakpoint(addr, condition=None, commands=None)` e o
  `GdbBackend`: criar o breakpoint, aplicar `condition N <expr>`, enviar o bloco
  `commands N ... end` e, em falha, remover o breakpoint e levantar `DebugError`. Verificar:
  testes unitários com fixtures do gdb para condição, comandos e rollback.
- [x] 1.2 Expor os parâmetros na tool `set_breakpoint`, devolver `number`/`addr` e documentar
  o padrão de auto-patch. Verificar: teste da tool com `Debugger` fake confirma a passagem de
  condição/comandos e a saída.

## 2. Backtrace com fallback de pilha

- [x] 2.1 Criar `domain/backtrace.py` com o scan puro de return addresses (regiões de código,
  alinhamento 2, dedupe, limite). Verificar: testes de domínio sem emulador (válidos, ímpares,
  fora de região, duplicados, limite).
- [x] 2.2 Criar `application/backtrace.py`: frames do gdb primeiro; se `< 4`, ler `pc`/`sp` e
  `sp..sp+0x800`, chamar o scan, confirmar cada candidato por `bl`/`blx` anterior e anexar com
  `source="stack"`; se a leitura falhar, devolver só o gdb. Verificar: testes com `Debugger`
  fake (bt curto, bt suficiente, dedupe, candidato sem chamada, falha).
- [x] 2.3 Adicionar `source` a `StackFrame` (default `"gdb"`) e incluí-lo na saída de
  `debug_backtrace`. Verificar: testes de serialização e descoberta.

## 3. Documentação

- [x] 3.1 Atualizar a skill com exemplos de condição/comandos (auto-patch) e a leitura do
  backtrace (`source="gdb"` × `"stack"`). Verificar: skill cita os dois usos.

## 4. Validação

- [x] 4.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-causal-debug-tools --strict` verdes.
- [x] 4.2 Smoke real com o emulador: criar breakpoint condicional e um com `commands`
  (`silent` + escrita + `continue`), conferir `list_breakpoints`, chamar `debug_backtrace`
  com alvo parado e remover tudo. Verificar: saídas coerentes, sem falso `error`.

> Validado em 2026-10-30: `pytest` (124), `pyright`, `lint-imports` e
> `openspec validate --strict` verdes. Smoke real no menu de status (KH): breakpoint em
> `0x020A11C4` parou; o gdb devolveu 2 frames e o fallback confirmou 10 return addresses por
> `bl`/`blx` (`source="stack"`). Condição `$r0 == 0` e `commands=["silent","continue"]` foram
> criados/listados; condição e comando inválidos fizeram rollback (sem breakpoint parcial).
