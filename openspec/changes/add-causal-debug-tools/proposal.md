## Why

A Onda 0 deu confiança ao ferramental. Falta o passo seguinte: responder **quem escreveu
isto** sem parar em milhares de eventos nem depender de um `bt` que rende ~2 frames. Na
sessão do menu de status isso custou uma maratona de NOPs para achar o `desenha_atributo`
certo e unwind manual da pilha para reconstruir a cadeia.

## What Changes

- `set_breakpoint(addr, condition, commands)` SHALL aceitar uma condição (registrador/memória)
  e uma lista de comandos gdb executados no hit. `commands` SHALL permitir o padrão de
  **auto-patch** (escrever um imediato e continuar) sem o loop manual
  `resume → wait → mem_write → resume`. Em falha de condição/comandos, o breakpoint SHALL ser
  removido e a tool SHALL retornar `error` + `hint`.
- `debug_backtrace` SHALL usar os frames do gdb e, quando eles forem insuficientes (< 4),
  **varrer a pilha** (`sp..sp+0x800`) por return addresses em ITCM/RAM principal/BIOS,
  alinhadas a 2 bytes (ARM/Thumb), sem duplicar o PC atual nem frames já conhecidos. Frames da
  pilha SHALL ser marcados com `source="stack"`; frames do gdb com `source="gdb"`.
- A skill do agente SHALL documentar o uso de condição/comandos e o novo backtrace.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-debug-tools`: breakpoints de código condicionais com comandos/auto-patch e backtrace
  com fallback de pilha.

## Impact

- MCP: `application/ports/debug.py` (assinatura de `set_breakpoint`), `infra/gdb.py`
  (condição/comandos/rollback), `domain/debug.py` (`StackFrame.source`),
  `domain/backtrace.py` (novo: scan puro), `application/backtrace.py` (novo: orquestração),
  `tools/debug.py` (tools e serialização), testes e skill.
- Emulador: **nenhuma mudança**.
- Sem custo por quadro; leitura de pilha só sob demanda no backtrace.
