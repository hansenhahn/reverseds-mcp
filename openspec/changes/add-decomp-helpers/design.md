## Context

Ver `proposal.md` — Why. O MCP já tem breakpoints condicionais, leitura de registradores/pilha,
`find_writer`/`find_reader`, símbolos persistentes e `disassemble`. Faltam três conveniências
de decomp que combinam essas peças.

## Goals / Non-Goals

**Goals:**
- `args_on_hit`: captura e checagem de argumentos por callsite (uma ou N execuções).
- `field_xref`/`field_writers`: acessos observados a um campo `[base+off]`, com símbolo.
- `struct_candidate`: esqueleto de struct a partir dos offsets/larguras vistos no código.

**Non-Goals:**
- Análise de fluxo/ponteiros completa (base register tracking) para o `struct_candidate`;
  ele é um **candidato** over-aproximado.
- Múltiplos hits por `field_xref` (uma chamada = um hit; repetir/rearmar fica para depois).
- Contratos complexos de tipos/structs; o schema é raso (registrador/palavra + token).
- Alterações no emulador/GDB stub.

## Decisions

- **`args_on_hit` síncrono.** Arma o breakpoint, usa `continue_` e captura; repete até
  `count` hits ou timeout. Ideal para callsites alcançáveis durante a espera; para transições
  de menu, o agente pode armar/`debug_resume` e disparar input antes. Alternativa: logging
  assíncrono no stub — maior escopo (2.2 é MCP).
- **Schema raso.** `dict[arg] = int | "ptr" | "nonzero" | "zero"`. `ptr` exige região mapeada
  que não seja ITCM/BIOS pequenos (para pegar `0x9` como inválido). Tokens desconhecidos são
  reportados como não checados, não como erro.
- **Pilha.** `stack_words` (default 8) palavras a partir de `sp`; o schema pode referenciar
  `stack0`, `stack1`… A leitura é `read_memory(sp, stack_words*4)`.
- **`field_xref` reusa `Watchpoints`.** `base` inteiro ou nome de símbolo (`SymbolTable.by_name`);
  `kind` `write`/`read`; retorna `pc`, `pc_hex`, `pc_symbol` e registradores. `field_writers`
  é alias de `kind="write"`.
- **`struct_candidate` estático.** Desmonta `code..code+size`, procura `[rN, #imm]` em
  loads/stores, ignora `sp`/`pc`, agrupa por offset (largura máxima) e gera C com padding.
  Inclui os registradores vistos para o agente refinar. Alternativa: rastrear o registrador
  base no runtime — follow-up.
- **Sem novo I/O no núcleo.** O `struct_candidate` lê memória pelo debugger (alvo parado) e
  desmonta com capstone; nada roda por quadro.

## Risks / Trade-offs

- [Callsite só ocorre durante uma transição] → `args_on_hit` pode expirar; usar
  `debug_resume`+input e depois `args_on_hit` se o callsite for recorrente; doc na skill.
- [Schema `ptr` falso positivo/negativo] → regra conservadora (região mapeada, exceto ITCM/BIOS
  pequenos); tokens desconhecidos ficam “não checados”.
- [`field_xref` um hit] → pode não representar todos os writers; repetir a chamada/`find_writer`.
- [`struct_candidate` ruidoso] → over-approxima por qualquer registrador; output inclui
  `registers`/`accesses` e é marcado como candidato.
- [Slots de watchpoint] → `field_xref` usa um slot; ver `debug_slots`.

## Migration Plan

Aditivo; novas tools e módulos. Validar com `pytest`, `pyright`, `lint-imports` e
`openspec validate --strict`; smoke opcional com o emulador para `args_on_hit`/`field_xref`.

## Open Questions

- `arg_log_bulk(range, cond)` num passe (P2) — depois.
- Base-register tracking/ponteiros no `struct_candidate` — follow-up.
