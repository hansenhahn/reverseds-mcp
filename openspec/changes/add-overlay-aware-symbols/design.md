## Context

Ver `proposal.md` — Why. A1/A2 (mergeado) já expõem candidatos de overlay e uma seleção ativa
(`overlay_select`), mas `SymbolTable` ainda resolve por endereço e `add` remove o mesmo endereço/nome
em qualquer overlay. O caso real: overlays 22 e 25 compartilham `0x02082960`; o mesmo endereço absoluto
pode ser funções diferentes. A resolução de símbolo precisa da mesma desambiguação.

O formato persistido (`symbols.json`) já inclui `overlay`; não há migração de dados.

## Goals / Non-Goals

**Goals:**
- Permitir dois símbolos no mesmo endereço em overlays diferentes, sem um apagar o outro.
- Resolver nome por `(addr, overlay)`, usando a overlay explícita ou a ativa (`overlay_select`).
- Carregar `.map` por unidade (`overlay=N`) sem contaminar outros overlays.
- Anotar disasm/backtrace/hits/watchpoints/`addr_valid` com o nome da overlay correta.
- Nunca escolher silenciosamente quando houver mais de um candidato.

**Non-Goals:**
- Detectar a overlay residente automaticamente (A1 usa seleção manual; o hook é D3).
- Resolver símbolos por overlay para ARM7 além do que a tabela já suporta.
- Mudar o formato do `symbols.json` ou o emulador.
- Criar edição/exclusão de símbolo além do necessário para recarregar um `.map`.

## Decisions

### 1. Identidade do símbolo = `(addr, overlay)`

`SymbolTable.add` passa a remover apenas símbolos com o mesmo `addr` **e** o mesmo `overlay`, e com o
mesmo `name` **e** o mesmo `overlay`. Assim:

- `Symbol(0x020A11C4, "fn_22", overlay=22)` e `Symbol(0x020A11C4, "fn_25", overlay=25)` coexistem.
- Um símbolo global (`overlay=None`) coexiste com os específicos e vira fallback.
- Recarregar o mapa da 25 substitui só os símbolos da 25; não apaga a 22.

**Alternativa considerada:** usar `name` como identidade global; descartado porque nomes podem se
repetir em overlays diferentes e o objetivo é justamente separar as unidades.

### 2. Resolução e ambiguidade

- `candidates(addr, overlay=None)`: considera os símbolos no **maior endereço ≤ `addr`**.
  - Com `overlay=N`: mantém `symbol.overlay == N` e globais (`overlay is None`); o específico tem
    precedência sobre o global no mesmo endereço.
  - Sem filtro: mantém todos; se houver mais de um no mesmo endereço, a lista é ambígua.
- `resolve(addr, overlay=None)`: devolve um único símbolo quando há um candidato claro; se a lista
  continuar ambígua, devolve `None` (não escolhe o primeiro).
- **Precedência nas tools:** `overlay=` explícito > overlay ativa (`overlay_select`) > sem filtro.
- `symbol_lookup`: se houver um único símbolo, retorna os campos atuais; se ambíguo, retorna
  `{ambiguous: true, symbols: [...]}` (sem `name` no topo), para o agente escolher.

**Alternativa considerada:** manter `resolve` sempre devolvendo o primeiro; descartado porque perpetua
o erro silencioso que A3 quer eliminar.

### 3. Overlay ativa sem abrir o canal de controle

`Bridge.active_overlay(core="arm9")` lê a seleção do `OverlayResolver` **já existente**, sem criar um
novo resolver nem conectar no control channel. Se não houver seleção, retorna `None`. As tools de
símbolo usam esse valor quando `overlay=` não é informado.

### 4. Carregamento de `.map` por unidade

`symbol_load(path, merge=True, overlay=None)`:

- `overlay=N`: todos os símbolos do `.map` são marcados com `overlay=N`.
- `merge=true`: adiciona/mescla; substitui apenas `(addr, N)`/`(name, N)`.
- `merge=false` + `overlay=N`: substitui **somente** os símbolos da overlay N, preservando globais e
  outras overlays.
- `merge=false` + `overlay=None`: substitui a tabela inteira (comportamento atual).

**Alternativa considerada:** adicionar uma coluna de overlay no `.map`; descartado para não inventar
formato. O parâmetro `overlay=` cobre o caso.

### 5. Anotações

- `disassemble(addr, count, mode, overlay=None)`: anota instruções e alvos de branch com a overlay
  explícita ou ativa.
- `debug_backtrace`, `find_writer`/`find_reader`, `hit_log_read`, `dma_source`, `args_on_hit` e
  `contract_check`: usam a overlay ativa; se ambíguo, deixam o símbolo `null` em vez de nome errado.
- `addr_valid`: cada candidato de overlay recebe o símbolo daquele overlay; o topo usa a seleção
  explícita/ativa (ou o único candidato).
- `symbol_define`/`symbol_list`/`symbol_lookup`: documentam overlay como parte da chave, não metadado.

### 6. Compatibilidade

- `symbols.json` permanece igual (já tem `overlay`).
- Símbolos antigos sem overlay continuam resolvendo como globais.
- `symbol_lookup` sem overlay e com um único símbolo mantém o formato atual; só o caso ambíguo muda.

## Risks / Trade-offs

- [Sem overlay ativa e dois nomes no mesmo endereço] → `ambiguous=true`/lista, nunca escolha silenciosa.
- [Seleção ativa stale após reload] → A1 já documenta revalidar; o símbolo não detecta sozinho.
- [`merge=false` com overlay] → semântica nova; documentar e testar para não apagar outras unidades.
- [Mesmo nome em overlays diferentes] → permitido pela chave `(name, overlay)`; listar/consultar com
  filtro.
- [Anotações antigas] → passam a usar a overlay ativa; sem seleção, preferem globais e evitam nome de
  overlay errada.
- [Performance] → a tabela é pequena e a busca continua O(n); sem impacto relevante.

## Migration Plan

Aditivo no domínio; a mudança de formato só ocorre no caso ambíguo de `symbol_lookup` (antes escolhia
um). Atualizar skill/docs. Validar com `pytest`, `pyright`, `lint-imports` e
`openspec validate --strict`; smoke real com 22/25 e dois símbolos no mesmo endereço.

## Open Questions

- `symbol_lookup` ambíguo deve retornar lista (`ambiguous=true`) ou erro + hint? (Proposta: lista.)
- Vale um `symbol_delete(addr, overlay=)` explícito? (Fora de escopo; `symbol_load(merge=false,
  overlay=N)` cobre o recarregamento.)
- Persistir a overlay ativa entre restarts? (D2, não aqui.)
