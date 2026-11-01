## Why

Inferir contratos de função e layout de struct no olho gera retrabalho: o C diz uma coisa, o
runtime faz outra, e offsets são descobertos um a um. Faltam ferramentas que (a) capturem os
argumentos reais em um callsite e comparem com um contrato, (b) liguem um campo `[base+off]`
aos Pcs que o leem/escrevem e (c) montem um esqueleto de struct a partir dos acessos.

## What Changes

- **`args_on_hit(addr, condition, count, timeout, stack_words, schema)`**: arma um breakpoint,
  captura `r0..r3`, `sp`, `lr`, `cpsr` e palavras da pilha em cada hit, e compara com um
  **schema** (inteiro, `ptr`, `nonzero`, `zero`), reportando divergências por argumento.
- **`field_xref(base, offset, kind)`** e **`field_writers(base, offset)`**: watchpoint de
  leitura/escrita em `base+offset`, com o símbolo do PC; `base` aceita endereço ou nome de
  símbolo. Retorna o hit (ou `null`).
- **`struct_candidate(code, size, mode)`**: varre uma faixa de código por `ldr/str` com
  deslocamento imediato, agrupa offset/largura/registradores e gera um **esqueleto C** de
  struct (candidato, over-approximado).
- Tudo no MCP; **sem mudança no emulador**.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-re-workflows`: adiciona os helpers de decomp `args_on_hit`, `field_xref`/
  `field_writers` e `struct_candidate`.

## Impact

- MCP: `domain/structs.py` (novo), `application/args.py` (novo), `tools/re.py`, testes.
- Emulador: **nenhuma mudança**.
