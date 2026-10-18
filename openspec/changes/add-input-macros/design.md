## Contexto

O input do melonDS é "segura/solta": `input.key` (máscara active-low) e `input.release`.
Não há noção de duração nem de sequência no canal.

## Decisões

### Onde implementar

No **MCP**, como um pequeno workflow que chama a porta `ControlChannel` em sequência, com
esperas (`time.sleep`).

Alternativa descartada: um **agendador no EmuThread** (frame-accurate). Custa no emulador
(preocupação do `config.yaml`) e não é necessário para menus — **YAGNI**. Fica como opção
futura (P2) caso precisemos de precisão de frame.

### Semântica

- `input_tap(mask, ms)`: `key(mask)` → espera `ms` → `release()`.
- `input_touch_tap(x, y, ms)`: `touch(x, y)` → espera `ms` → `release()`.
- `input_sequence(steps)`: para cada passo: segura o input (`key(mask)` **ou**
  `touch(x, y)`) → espera `ms` → `release()` → espera `after_ms`. Passo sem input
  (ou `mask=0xFFF`) = apenas espera.
- Sanidade: limitar o tempo total da sequência (evitar trava acidental por `after_ms` enorme).

### Toque (tela de baixo)

O input também precisa cobrir a **tela de toque** (tela de baixo / engine B), porque há jogos
**touch-only** (ex.: Hotel Dusk) que não usam botões. Usa-se `input.touch {x, y}` +
`input.release`, com as **mesmas semânticas** (tap e passo de sequência) e o mesmo teto de
tempo. No passo, `touch` (x,y) e `mask` são **mutuamente exclusivos**; as coordenadas são
validadas no domínio (`0<=x<256`, `0<=y<192`). Assim dá para **intercalar** toque e botões.

### Erros

- Falha do canal → erro claro; a sequência **aborta no primeiro erro**.
- O input SHALL ser solto no fim, mesmo em erro (`finally` → `input.release`).

## Riscos

- Timing depende do SO (não frame-accurate) — suficiente para transições de menu.
- Não usar em concorrência com outro consumidor mexendo no mesmo input.
