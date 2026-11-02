# add-overlay-aware-symbols

A3 da Frente A: símbolos por overlay.

- Chave do símbolo passa a ser `(addr, overlay)`; dois overlays podem ter nomes no mesmo endereço.
- Consulta/lista usam overlay explícita > `overlay_select` ativo > sem filtro; ambiguidade vira
  `ambiguous=true` + lista, não primeiro match.
- `symbol_load(overlay=N)` marca o `.map`; `merge=false` + overlay substitui só aquela unidade.
- Anotações (disasm/backtrace/hits/watchpoints/`addr_valid`) usam a overlay ativa.

Sem mudança no emulador. Depende de A1/A2 (`overlay_select`/candidatos).
