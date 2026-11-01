## Context

Ver `proposal.md` — Why. O estado atual:

- `domain/symbols.py`: `Symbol{addr,name}` e `SymbolTable.from_map` (linhas `address name`),
  `resolve` por “maior endereço ≤”. Apenas em memória; `symbol_load` **substitui** a tabela.
- `tools/debug.py`: `disassemble` devolve endereço/bytes/mnemônico/operandos, sem símbolos.
- `tools/re.py`: `symbol_lookup` resolve, mas o resto (`find_*`, `hit_log_read`, `addr_valid`)
  não anota.
- Não há armazenamento de snippets C+ASM.

## Goals / Non-Goals

**Goals:**
- Definir aliases uma vez, persistir e anotar disasm/backtrace/hits/addr_valid.
- Carregar `.map` e **mesclar** com aliases; sobreviver ao restart.
- Guardar snippets C+ASM por endereço.
- Thread-safe no servidor MCP (tools concorrentes).

**Non-Goals:**
- Ghidra/export/import externo.
- Tipos ricos de Ghidra, assinatura completa de função, tamanho de símbolo.
- Resolução overlay-aware (o campo `overlay` é armazenado, mas a resolução continua por
  endereço; overlays que compartilham base ficam para um follow-up).
- `args_on_hit`/`field_xref`/`struct_candidate` (2.2), display↔RAM (2.3),
  contract/diff (2.5) e `rom_details` (2.6).

## Decisions

- **Modelo `Symbol{addr, name, kind="label", comment=None, overlay=None}`.** `kind` é
  `function`/`label`/`data`/`struct` (string livre); `overlay` é metadado. Mantém o `.map`
  simples compatível.
- **`SymbolTable` thread-safe e puro.** `add`/`merge`/`resolve`/`all`/`to_json`/`from_json`
  com `RLock`; sem I/O. `add` substitui o mesmo endereço e remove duplicata do mesmo nome.
- **Persistência em `symbols.json` no out dir.** `Bridge` carrega lazy na primeira leitura e
  grava após `symbol_define`/`symbol_load`. JSON versionado (`{"symbols":[...]}`), tolerante a
  arquivo ausente/corrompido (avisa e começa vazio).
- **`symbol_load` mescla por padrão.** `merge=False` permite substituir; o `.map` é parseado
  como antes (`address name`), e os campos ricos vêm dos aliases.
- **Anotação sem inventar.** `disassemble` usa `resolve(addr)` (mais próximo ≤) e extrai o
  primeiro `0x...` de `op_str` para o alvo; `backtrace` só preenche `function` quando o gdb
  devolveu `None`, mantendo o nome do gdb quando existir.
- **Snippets em `application/decomp.py`.** Serviço sobre `FileStore`; JSON
  `{"0xADDR":{"c":...,"asm":...}}`; `decomp_snippet(addr,c,asm)` grava e devolve o estado.
  Alternativa: JSON direto na tool — misturaria transporte e persistência.
- **Sem Ghidra.** O modelo é interno; um exportador pode ser adicionado depois sem mudar o
  formato persistido.

## Risks / Trade-offs

- [Símbolo “mais próximo ≤” pode rotular instruções de outro bloco] → documentado; função com
  tamanho/símbolos overlay-aware fica para follow-up.
- [Aliases duplicados/endereço compartilhado por overlays] → `add` substitui por endereço;
  `overlay` fica como metadado e a resolução overlay-aware é follow-up.
- [JSON concorrente/corrompido] → lock no `SymbolTable`/bridge; escrita atômica via `OutDir`
  (write_text) e leitura tolerante.
- [Snippet grande no JSON] → snippets são curtos (C+ASM de um trecho); sem limite rígido nesta
  versão.

## Migration Plan

Aditivo: `Symbol` ganha campos com default; `symbol_load` passa a mesclar e persistir. O
`symbols.json` é criado sob demanda; sem arquivo, comportamento atual. Validar com `pytest`,
`pyright`, `lint-imports` e `openspec validate --strict`.

## Open Questions

- Exportar para Ghidra depois (CSV/script) — fora deste change.
- Símbolos por overlay com a mesma base — follow-up (precisa do overlay carregado no PC).
