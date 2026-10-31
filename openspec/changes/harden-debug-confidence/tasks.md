## 1. Watchpoints: report, list e remove

- [x] 1.1 Adicionar fixtures com saídas **reais** do `gdb-multiarch` para criação
  (`Hardware watchpoint`, `Hardware read watchpoint`, `Hardware access watchpoint`) e para
  `info breakpoints` (`hw watchpoint`, `read watchpoint`, `acc watchpoint`, com/sem
  `stop only if`). Verificar: os testes de parse falham antes da correção (mostram o bug) e
  passam depois.
- [x] 1.2 Corrigir o regex de `set_watchpoint` para aceitar read/access e retornar o número,
  incluindo a variante real `Hardware access (read/write) watchpoint N`. Verificar: teste
  unitário para os quatro formatos → `set_watchpoint` devolve o número, sem `DebugError`.
- [x] 1.3 Trocar o `_BP_RE` por parse por colunas (`Type`, `Disp`, `Enb`, `What`) e normalizar
  `kind` em `breakpoint`/`watchpoint`/`read-watchpoint`/`access-watchpoint`. Verificar:
  teste com fixture de `info breakpoints` cobre os quatro tipos, endereço e condição.
- [x] 1.4 Fazer `remove` checar a saída (`No breakpoint number`/`not found`) e levantar
  `DebugError` com mensagem clara; sucesso nos casos válidos. Verificar: teste com saída de
  erro e com `Deleted breakpoint`.
- [x] 1.5 Ajustar `list_breakpoints`/`debug_error` para o novo `kind` e para hint de recursos
  esgotados (`not enough hardware resources`/`Cannot allocate` → aponta
  `debug_slots`/`list_breakpoints`). Verificar: teste da tool com `Debugger` fake devolve
  `error` + `hint`; teste de listagem preserva os tipos.

- [x] 1.6 Distinguir **hardware × software**: `Breakpoint.hardware` (derivado do `Type`) e
  `debug_slots` contando só hardware, com `software_watchpoints` à parte. Verificar: teste
  unitário de parse e de `HardwareSlots`; smoke real com 4 WPs + 1 fallback.

## 2. Diagnóstico de slots de hardware

- [x] 2.1 Acrescentar `watchpoint_limit()` e `core()` à porta `Debugger`; em `GdbBackend`,
  extrair `WATCHPOINT_LIMIT = 4` (usado no `_start`) e retornar `self._core`. Atualizar o
  `FakeDebugger` dos testes. Verificar: `uv run pyright` verde; teste unitário do backend
  devolve limite 4 e o core conectado.
- [x] 2.2 Implementar a tool `debug_slots` em `tools/debug.py`, compondo
  `watchpoint_limit()`, `core()` e `breakpoints()`: limite, usados, livres, contagem por tipo
  e lista. Verificar: teste com fake (2 watchpoints → usados 2, livres 2; nenhum → 0 usados).
- [x] 2.3 Garantir descoberta da tool no servidor. Verificar: teste de `list_tools` inclui
  `debug_slots`.

## 3. Validação de endereços

- [x] 3.1 Criar `domain/addresses.py` com `MemoryRegion`, a tabela `NDS9_REGIONS`,
  `parse_address()` e `describe_address()` (sem I/O). Cobrir: `0x...`, decimal, texto com
  `A-F` sem prefixo, inválido, alinhamento de 4, RAM/VRAM/OAM/IO/BIOS e endereço não mapeado.
  Verificar: testes unitários de domínio (sem emulador) verdes.
- [x] 3.2 Implementar `addr_valid(value)` em `tools/re.py` usando o domínio e resolvendo
  overlay via `bridge.overlays()` quando a ROM estiver disponível; sem ROM, `overlay: null`
  sem falhar. Verificar: testes com fake de overlays e com `NdsRomError`/`ControlError`;
  `parse_address` inválido → `error` + `hint`.
- [x] 3.3 Ecoar o endereço normalizado em `set_breakpoint` (`addr`) e `mem_write`
  (`addr` + `size`). Verificar: testes das tools conferem os campos; nenhum campo existente
  é removido.

## 4. Documentação

- [x] 4.1 Atualizar `.opencode/skills/reverse-engineering-ds/SKILL.md`: incluir `debug_slots` e
  `addr_valid` no toolchain, um bloco "Confiança" (validar endereço antes de escrever; provar
  a escrita com watchpoint; conferir slots antes de culpar o stub) e incorporar o fluxo de
  7 fases/anti-padrões da metodologia. Verificar: leitura da skill cita as duas tools, o
  checklist e o fluxo canônico.
- [x] 4.2 Registrar `harden-debug-confidence` na Onda 0 do `ROADMAP.md` (change em andamento).
  Verificar: a seção da Onda 0 aponta o change.

## 5. Validação final

- [x] 5.1 `uv run python -m pytest`, `uv run pyright` e `uv run lint-imports` verdes.
  Verificar: três comandos sem erro (contratos de camada preservados; `domain/addresses.py`
  não importa application/infra/tools).
- [x] 5.2 `openspec validate harden-debug-confidence --strict` OK. Verificar: comando sem
  erro.
- [x] 5.3 Smoke com o emulador real (watchpoints): criar `rwatch`/access, conferir
  `list_breakpoints`/`debug_slots` (hardware × software), remover e validar que sumiu.
  Verificar: feito em 2026-10-30 — read/access criados e listados, remove OK, 4 slots de HW
  e fallback de software contabilizados corretamente; sem falso `error`. Nota do stub:
  `access` sozinho funciona; `access` coexistindo com outro WP pode ser recusado por recursos.
- [x] 5.4 Smoke de `addr_valid` com **overlay real**: após rebuild do emulador (`-j 1`) com
  `rom.info`/`rom.read`, `0x020A11C4` resolveu para **overlay 22**, base `0x02082960`,
  offset `0x1E864`; `rom_info` e `cart_list` (1596 arquivos) OK.
  Verificar: feito em 2026-10-30 contra `xpa-khe.nds`.
