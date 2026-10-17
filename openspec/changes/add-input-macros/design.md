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
- `input_sequence(steps)`: para cada passo: `key(mask)` → espera `ms` → `release()` →
  espera `after_ms`. Passo sem `mask` (ou `mask=0xFFF`) = apenas espera.
- Sanidade: limitar o tempo total da sequência (evitar trava acidental por `after_ms` enorme).

### Erros

- Falha do canal → erro claro; a sequência **aborta no primeiro erro**.
- O input SHALL ser solto no fim, mesmo em erro (`finally` → `input.release`).

## Riscos

- Timing depende do SO (não frame-accurate) — suficiente para transições de menu.
- Não usar em concorrência com outro consumidor mexendo no mesmo input.
