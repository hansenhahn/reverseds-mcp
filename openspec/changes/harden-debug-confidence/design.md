## Context

Ver `proposal.md` — Why. O estado atual que molda o approach:

- `infra/gdb.py` é um **parser de texto** sobre `gdb-multiarch` (sem MI). O regex de criação
  de watchpoint (`set_watchpoint`) só reconhece `Hardware watchpoint`/`Watchpoint`; para
  `rwatch`/`awatch` o gdb responde `Hardware read watchpoint N` / `Hardware access watchpoint
  N` → o MCP devolve `error` falso, embora o watchpoint tenha sido criado.
- O `_BP_RE` de `info breakpoints` só casa `breakpoint|watchpoint|hw watchpoint|hw
  breakpoint`; os tipos `read watchpoint` e `acc watchpoint` ficam de fora e o `kind` é
  reduzido a `watchpoint`/`breakpoint`, perdendo a distinção de acesso.
- `remove()` executa `delete N` e ignora a saída; um número inexistente vira "sucesso".
- O limite de watchpoints de hardware (`set remote hardware-watchpoint-limit 4`) é um literal
  em `_start`; nenhuma tool o expõe. Em falha por recursos, o erro não diz o que está ocupado.
- Não há validação de endereço: hex/dec é conferido à mão (já gerou patch no lugar errado) e
  a região/overlay só é descoberta por outra tool (`overlay_for_address`).
- A skill do agente já cobre o fluxo geral, mas não cita `debug_slots`/`addr_valid` nem o
  checklist de confiança.

## Goals / Non-Goals

**Goals:**
- Report/list/remove de watchpoints **confiável** para write/read/access.
- Diagnóstico de **slots de hardware** por core conectado, com hint acionável.
- `addr_valid` puro e rápido (hex/dec, alinhamento, região, overlay) para confirmar endereço
  antes de qualquer `mem_write`/breakpoint.
- Documentar as duas tools e as regras de confiança na skill.

**Non-Goals:**
- Non-stop, hit log, breakpoint condicional (Onda 1).
- Limpar watchpoints órfãos automaticamente (remoção é explícita).
- Reescrever o parser em gdb/MI.
- Mapa completo do ARM7 (só ARM9 nesta onda; ARM7 fica para quando houver demanda).

## Decisions

- **Regex de criação tolerante a espaço e variante.** Aceitar
  `(?:Hardware (?:read |access )?watchpoint|Watchpoint) (\d+)`, que cobre
  `Hardware watchpoint`, `Hardware read watchpoint`, `Hardware access watchpoint` e o caso
  sem `Hardware`. Alternativa: uma regex por tipo (mais código, mesma cobertura).
- **`_BP_RE` por colunas, não por lista fechada de tipos.** O campo `Type` do gdb pode ter
  espaço (`hw watchpoint`, `read watchpoint`, `acc watchpoint`) e a `Disp` é
  `keep|del|dis`. Parse:
  `^(\d+)\s+(.+?)\s+(keep|del|dis)\s+([yn])\s+(.*)$` e normalize:
  `breakpoint` se contém `breakpoint`; `read-watchpoint` se contém `read`;
  `access-watchpoint` se contém `acc`; senão `watchpoint`.
  Mantém `breakpoint`/`watchpoint` para os casos antigos (sem quebra).
- **`remove` verifica a saída.** Se vier `No breakpoint number`/`not found`, levanta
  `DebugError` com mensagem clara; caso contrário, sucesso. Alternativa: consultar
  `breakpoints()` antes (mais I/O e corrida com o stub).
- **`debug_slots` como tool fina sobre a porta.** Adicionar à porta `Debugger`:
  `watchpoint_limit() -> int` e `core() -> str | None`. `GdbBackend` expõe
  `WATCHPOINT_LIMIT = 4` (o mesmo valor aplicado em `_start`) e `self._core`. A tool conta
  **apenas** watchpoints de hardware (`Breakpoint.hardware`), calcula livres
  (`max(0, limit - usados)`) e reporta à parte os watchpoints em fallback de software.
  Alternativa: hardcodar 4 na tool (duplicaria a configuração e mentiria se o limite mudar).
- **Distinguir hardware × software.** `info breakpoints` usa `hw watchpoint` para hardware
  de escrita e `watchpoint` para o fallback de software; read/access não têm prefixo `hw`,
  mas são hardware. `Breakpoint.hardware` é derivado disso e `debug_slots` não conta o
  fallback como slot. O gdb real também responde `Hardware access (read/write) watchpoint N`
  (não só `Hardware access watchpoint N`) — o regex cobre as duas formas.
- **Hint de recursos em `tools/app.py`.** `debug_error` reconhece
  `not enough hardware resources`/`Cannot allocate` e anexa hint para `debug_slots`/
  `list_breakpoints`. Mantém o contrato `{error,hint}` num único lugar.
- **`addr_valid`: domínio puro + orquestração mínima na tool.** Novo `domain/addresses.py`
  com `MemoryRegion`, a tabela `NDS9_REGIONS`, `parse_address()` e `describe_address()` —
  sem I/O. A tool em `tools/re.py` faz o parse, chama o domínio e, **opcionalmente**, resolve
  overlay via `bridge.overlays()` (mesmo padrão de `overlay_for_address`), tolerando ROM
  ausente (`NdsRomError`/`ControlError` → `overlay: null`). Alternativa: um serviço em
  `application/` só para um lookup — YAGNI; o padrão existente já é tool→bridge.
- **Regras de parse de endereço.** Inteiro: aceitar `0..0xFFFFFFFF`. Texto: `0x...` é hex;
  só dígitos é decimal; se contiver `A-F` (sem `0x`), tratar como hex (caso comum de dump);
  qualquer outro texto → `ValueError` com hint do formato. Normalizar sempre para `0x%08x`.
- **Tabela de regiões do ARM9 (GBATEK).** ITCM, DTCM (base padrão), Main RAM, Shared WRAM,
  I/O, paletas, VRAM A/B (BG e OBJ), LCDC, OAM, GBA ROM/RAM e ARM9 BIOS. Lacunas ficam
  `mapped=false` (não é erro: pode ser região dependente de VRAMCNT/CP15).
- **Eco do endereço.** `set_breakpoint` e `mem_write` acrescentam `"addr": "0x..."` (e
  `"size"` no write) — aditivo, não muda o contrato atual.
- **Docs na skill.** Acrescentar as tools novas ao toolchain e um bloco "Confiança" com:
  validar endereço antes de escrever; provar a escrita (watchpoint) em vez de concluir por
  NOP; conferir slots antes de culpar o stub.

## Risks / Trade-offs

- [Saída do gdb varia entre versões (`acc watchpoint` × `access watchpoint`,
  `Hardware access (read/write) watchpoint`, `Disp`)] → regex por colunas + normalização
  tolerante + fixtures reais no teste.
- [gdb cai para watchpoint de software quando o hardware esgota] → `debug_slots` reporta
  `software_watchpoints` e não conta esses como slot; o agente vê a diferença.
- [watchpoint de acesso pode falhar ao coexistir com outros no stub] → erro + hint
  (slots/tipo não suportado); validar por `debug_slots`/`list_breakpoints`.
- [Limite de HW por core pode ser menor que 4] → `debug_slots` reporta o limite configurado;
  documentar que o valor efetivo é o do `set remote hardware-watchpoint-limit`.
- [`info breakpoints` não vê watchpoints órfãos no stub] → limitação documentada; a remoção
  explícita continua sendo o caminho.
- [Mapa de regiões incompleto (DTCM moveable, janelas de VRAM dependem de VRAMCNT)] →
  retornar `mapped=false` em vez de erro; o overlay é resolvido pela tabela da ROM.
- [Resolver overlay sem ROM] → `addr_valid` continua funcionando com `overlay: null`.
- [Mudança de `kind` para read/access] → só acrescenta valores novos; write continua
  `watchpoint`; testes existentes ajustados.

## Migration Plan

Aditivo: tools novas (`debug_slots`, `addr_valid`) e campos novos no retorno
(`addr`/`size`, `kind` mais específico). Nenhuma tool existente quebra. Atualizar testes e a
skill. Validar com `uv run pytest`, `uv run pyright`, `uv run lint-imports` e
`openspec validate harden-debug-confidence --strict`; smoke opcional com o emulador para
criar/listar/remover um `rwatch` real.

## Open Questions

- Vale a pena, numa próxima onda, `addr_valid` também para o ARM7? (Fora de escopo aqui.)
- `debug_slots` deve oferecer um `clear` em massa? (Não nesta onda; remoção explícita.)
