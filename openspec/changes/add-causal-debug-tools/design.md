## Context

Ver `proposal.md` — Why. Estado atual:

- `set_breakpoint(addr)` só cria o breakpoint; não há condição nem ações no hit. O agente
  filtra depois, parando em tudo (milhares de glifos/draws), ou monta o loop manual
  `debug_resume → debug_wait → mem_write → debug_resume`.
- `GdbBackend.backtrace()` apenas parseia o `bt` do gdb. Sem unwind info no ARM, o `bt`
  costuma devolver ~2 frames; o resto da cadeia fica manual (dump da pilha + leitura visual).
- `StackFrame` não distingue a origem do frame.

## Goals / Non-Goals

**Goals:**
- Condição por expressão gdb e comandos no hit (incluindo auto-patch + continue).
- Falha de configuração não deixa breakpoint parcial.
- Backtrace com fallback de pilha, marcando a origem de cada frame.
- Tudo testável sem emulador (domínio + fakes).

**Non-Goals:**
- Simbolização automática dos frames de pilha (Onda 2, símbolos/aliases).
- Non-stop e hit log (itens 1.5+).
- Hit log em massa; `commands` é por breakpoint.

## Decisions

- **`commands` são comandos gdb crus, uma linha cada.** A tool passa a lista para o bloco
  `commands N ... end`, com validação de linha vazia, `end` ou newline embutido. Mantém o
  poder do gdb (ex.: `set {unsigned int}0xADDR = 0xVALUE`, `continue`, `silent`) sem inventar
  uma DSL. Alternativa: um `auto_patch` estruturado — menos flexível e mais código.
- **Auto-patch = `commands`.** O padrão recomendado é
  `["silent", "set {unsigned int}0xADDR = 0xVALUE", "continue"]`. Atende ao caso da sessão
  (corrigir um imediato ao passar por um callsite) sem loop manual.
- **Rollback em falha.** Se `condition` ou `commands` falharem (gdb reporta `No symbol`/
  `error`/`Invalid`), o backend remove o breakpoint recém-criado e levanta `DebugError`.
  Alternativa: deixar o breakpoint meio configurado — pior para o agente.
- **Backtrace: gdb primeiro, pilha como fallback.** Se o `bt` devolver < 4 frames, o serviço
  lê `pc`/`sp`, lê `sp..sp+0x800` e chama um scan puro. Frames do gdb vêm primeiro; os
  candidatos entram depois, com `source="stack"`. Evita custo/ruído quando o gdb já resolveu.
- **Candidato só vale se for retorno de chamada.** Antes de aceitar um endereço, o serviço lê
  os 4 bytes anteriores e confirma, em ARM ou Thumb, que são um `bl`/`blx` que termina no
  candidato. Isso elimina dados pequenos/ponteiros que só “parecem” código (visto no smoke).
- **Alinhamento de 2 bytes, não 4.** NDS usa ARM **e** Thumb; return addresses de Thumb podem
  ser `2 mod 4`. O scan aceita endereços pares, em ITCM/RAM principal/BIOS, descarta PC atual
  e frames já vistos, deduplica e limita a 32 candidatos. Alternativa: só ARM (perde Thumb).
- **Falha ao ler a pilha não derruba o backtrace.** Se `read_memory` falhar, devolve os frames
  do gdb (sem inventar frames). Alternativa: erro — menos útil para o agente.
- **`StackFrame.source`.** Campo novo com default `"gdb"`; a tool inclui `source` na saída.
  Aditivo e testável.

## Risks / Trade-offs

- [Scan ainda pode gerar falso positivo em dado que imita uma chamada] → validação por
  BL/BLX + `source="stack"` + limite; o agente confirma o callsite.
- [Comandos gdb variam por versão] → comandos crus + validação de bloco; exemplos na skill.
- [Condição/comandos com erro silencioso] → checar saída por `No symbol`/`error`/`Invalid` e
  fazer rollback; testes com fixtures.
- [Thumb 32-bit/second half de BL] → scan por palavra de 32 bits na pilha (return address é
  escrito inteiro) e alinhamento par; suficiente para o fallback.

## Migration Plan

Aditivo: `set_breakpoint` ganha parâmetros opcionais; `StackFrame` ganha `source` com default;
a saída de `debug_backtrace` ganha `source`. Nenhuma tool quebra. Atualizar testes, fakes e a
skill. Validar com `pytest`, `pyright`, `lint-imports`, `openspec validate --strict` e smoke
real (breakpoint condicional/comandos e backtrace com alvo parado).

## Open Questions

- Vale a pena um `run_until(addr, condition)` atômico depois? (P2 do roadmap; fora deste change.)
- Anotar os frames de pilha com símbolos/aliases? Fica para a Onda 2.
