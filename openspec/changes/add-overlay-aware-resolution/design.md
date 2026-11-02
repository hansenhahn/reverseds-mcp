## Context

Ver `proposal.md` — Why. Hoje `OverlayTable.for_address` devolve o primeiro overlay que cobre
o endereço (`domain/overlays.py`). `ChannelRom.overlay_for_address` só repassa esse resultado
(`infra/ndsrom.py`), e `rom_details`/`addr_valid` o consomem. O `Overlay` do domínio guarda
apenas `core`, `index`, `ram_address`, `ram_size`, `bss_size` e `file_id`; os campos
`sinit_start/end` e o último word do y9 são ignorados. O FAT já é lido por `NdsFs`, mas não há
API pública para obter o `file_offset`/`file_size` de um `file_id`.

O caso real que motiva o change: overlays 22 e 25 compartilham `0x02082960`; o primeiro match
pode ser 22. No caso do load screen, a overlay 0 tem um prefixo de `0x600` antes do código, o
que separa `offset_file` (`addr - ram_address`) de `offset_code` (`addr - code_base`).

**Dependências:** este change assume `addr_valid` (`harden-debug-confidence`) e `rom_details`
(`add-rom-details`), ambos implementados mas ainda **não arquivados**. Arquivar este change
depois deles (ou junto), para que as specs base já contenham as tools que ele modifica.

## Goals / Non-Goals

**Goals:**
- Devolver **todos** os overlays candidatos para um endereço e sinalizar ambiguidade.
- Permitir ao agente declarar a overlay residente (`overlay_select`) e, opcionalmente, a base
  de código/prefixo, sem depender de detecção no emulador.
- Expor detalhes completos do overlay: y9 + FAT + compressão + sinit.
- Separar explicitamente `offset_file` e `offset_code`.
- Manter compatibilidade dos campos `overlay`/`offset` existentes sempre que não houver
  ambiguidade.

**Non-Goals:**
- Detectar automaticamente qual overlay está residente (isso exige o hook
  `overlay_loaded`, que pertence à frente D do roadmap).
- Inferir o prefixo/base de código (é específico do jogo; o caller informa).
- Resolver símbolos por overlay (A3; change separado).
- Descomprimir overlay ou validar o formato BLZ/LZ; só reportar o que o y9/FAT dizem.
- Mudar o emulador.

## Decisions

### 1. Modelo de domínio: `Overlay`, `OverlayHit`, `OverlayDetails`

- **`Overlay`** ganha `sinit_start`, `sinit_end`, `flags` e `compressed_size` (campos crus do
  y9). `file_offset`/`file_size` **não** entram no `Overlay` puro, porque dependem do FAT.
- **`OverlayDetails`** (novo `@dataclass(frozen=True, slots=True)`) combina `Overlay` +
  `file_offset`, `file_size`, `compressed`, `compressed_size` e, opcionalmente,
  `code_base`/`prefix_size`. É montado pelo adaptador, que tem acesso ao FAT.
- **`OverlayHit`** ganha `offset_file` e `offset_code: int | None`. O campo `offset` existente
  vira propriedade que devolve `offset_file`, preservando os callers atuais.
- **`OverlayTable.candidates(addr)`** devolve `tuple[OverlayHit, ...]` com **todos** os
  overlays que cobrem o endereço. `for_address` continua devolvendo o primeiro para
  compatibilidade (mas os tools deixam de usá-lo para decidir).

**Alternativas consideradas:**
- Fazer `for_address` devolver uma lista: quebra a assinatura e todos os callers; descartado.
- Colocar `file_offset`/`file_size` no `Overlay` e fazer o parser y9 ler o FAT: acopla o
  parser puro ao filesystem; descartado.
- Detectar a overlay residente pelo `pc`/bytes: não há sinal confiável sem hook do emulador;
  descartado por enquanto.

### 2. Seleção ativa e base de código

Novo serviço de aplicação `OverlayResolver` (em `application/overlays.py`) sobre a porta
`Overlays`:

- `select(index, core, code_base=None)` / `clear(core)` guardam a seleção em memória.
- `candidates(addr, core)` devolve todos os hits.
- `details(index, core, code_base=None)` devolve `OverlayDetails`; se `code_base` não vier,
  usa a base configurada na seleção (se houver) ou `None`.
- `resolve(addr, core, overlay=None, code_base=None)` escolhe: `overlay` explícito > seleção
  ativa > único candidato; se houver mais de um e nada selecionado, `overlay=None` +
  `ambiguous=true`.

A seleção é **estado de sessão**, não persistida. Ela não prova residência: é uma declaração
do agente, coerente com “não há detecção automática neste change”. Após reload de overlay o
agente deve revalidar (`overlay_select` de novo).

`code_base` é validada em `[ram_address, ram_address + ram_size)`; `prefix_size =
code_base - ram_address`. Sem `code_base`, `offset_code=None` e `prefix_size=None`; nunca se
assume `code_base == ram_address` para “inventar” um offset de código.

**Alternativas consideradas:**
- Guardar `code_base` no `Overlay` lido do y9: não existe campo para isso; descartado.
- Derivar `code_base` de `sinit_start/end`: no caso observado o sinit aponta para o fim do
  código, não para o prefixo; descartado.
- Parâmetro `prefix=` em vez de `code_base=`: equivalente; `code_base` é mais direto para
  validar o intervalo e calcular `offset_code`.

### 3. Compressão a partir do y9 + FAT

O último word do y9 é “Reserved (zero)” no GBATEK, mas em ROMs observadas ele carrega o
**tamanho comprimido** nos 24 bits baixos (com flags no byte alto). O FAT dá o tamanho real do
arquivo. Decisão:

- `file_size` = `Fat.span(file_id).size` (autoritativo).
- `compressed_size = flags & 0x00FFFFFF` quando nonzero; senão `0`.
- `compressed = file_size < ram_size` (fallback: `0 < compressed_size < ram_size`).
- `flags` cru sempre é devolvido; se o campo for zero (GBATEK clássico), `compressed=false`.

Isso evita depender de um único campo reservado e mantém o comportamento correto para ROMs
sem compressão.

### 4. Tools e compatibilidade

- `overlay_for_address(addr, core="arm9", overlay=None, code_base=None)` devolve
  `{found, ambiguous, overlays: [...], overlay: <selecionado|único|null>, offset_file,
  offset_code}`. `offset` continua como alias de `offset_file`.
- `overlay_details(index, core="arm9", code_base=None)` devolve os campos do y9 + FAT +
  compressão + `code_base`/`prefix_size` (quando conhecidos).
- `overlay_select(index=None, core="arm9", code_base=None)` seleciona/limpa; devolve o estado
  atual (`core`, `overlay`, `code_base`, `prefix_size`).
- `rom_details(overlay=None, code_base=None)` mantém o formato atual, mas `runtime` ganha
  `overlays` e `ambiguous`; `runtime.overlay` passa a ser `null` quando ambíguo e nada foi
  selecionado (em vez de um primeiro match errado).
- `addr_valid(value, overlay=None, code_base=None)` ganha `overlays`, `ambiguous` e, por
  candidato, `offset_file`/`offset_code`; `overlay`/`offset` continuam para compatibilidade.

**Alternativa considerada:** mudar `rom_details.runtime.overlay` para lista sempre; descartado
para não quebrar consumidores que esperam um objeto. O campo `overlays` é aditivo; `overlay`
vira `null` só no caso ambíguo, que antes era um erro silencioso.

### 5. Camadas

- `domain/overlays.py`: tipos puros + `candidates`; sem I/O.
- `application/overlays.py`: `OverlayResolver` (orquestra a porta e mantém seleção).
- `application/ports/overlays.py`: `overlay_candidates`, `overlay_details`.
- `infra/ndsrom.py`: parse do y9 (sinit/flags), FAT span, montagem de `OverlayDetails`.
- `bridge.py`: expõe `overlay_resolver()`.
- `tools/cart.py` / `tools/re.py`: transporte.

## Risks / Trade-offs

- [Campo reservado do y9 ser zero em outra ROM] → usar `file_size < ram_size` como sinal
  principal; `flags` cru fica disponível para inspeção.
- [Seleção ativa ficar stale após reload] → é estado de sessão explícito; documentar que o
  agente deve revalidar. Não há detecção automática neste change.
- [Ambiguidade sem seleção] → `overlay=null` + `ambiguous=true`; o agente precisa escolher. É
  melhor que um primeiro match silencioso.
- [`rom_details.runtime.overlay` mudar de objeto para `null`] → só no caso ambíguo, onde o
  valor anterior era potencialmente errado; atualizar skill/docs.
- [Prefixos específicos de jogo] → `code_base` é opcional e explícito; o MCP não inventa.
- [Custo de FAT] → o FAT já é carregado com a ROM; `overlay_details` é sob demanda.

## Migration Plan

Aditivo, exceto o caso ambíguo de `rom_details.runtime.overlay` (antes errado, agora `null`).
Atualizar skill/docs para `overlays`/`ambiguous` e para `offset_file` × `offset_code`.
Validar com `pytest`, `pyright`, `lint-imports` e `openspec validate --strict`; smoke real com
overlay 22/25 (base compartilhada) e overlay 0 (prefixo `0x600`).

## Open Questions

- Vale expor `overlay_candidates` também para ARM7 na mesma tool? (O parser já é genérico;
  `addr_valid` continua ARM9-only.)
- Persistir a seleção de overlay entre restarts? (Fora de escopo; seria sessão salvável, D2.)
- Adicionar um hook `overlay_loaded` no emulador para substituir a seleção manual? (Frente D3.)
