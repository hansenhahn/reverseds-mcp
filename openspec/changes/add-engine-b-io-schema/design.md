## Context

Ver `proposal.md`. O schema atual (`domain/io/registers/video.py`) cobre 11 registradores de
vídeo; faltam scroll, janelas, mosaic e blending. O decode é puro (`Register.decode`) e a
leitura passa pelo debugger (`IoReader.read`). O `LIMITACOES.md` §3 mostrou que a engine B
não é coberta e que alguns registradores write-only leem 0.

## Goals / Non-Goals

**Goals:**
- Cobrir scroll, janelas, mosaic e blending nas engines A e B com bitfields nomeados.
- Expor `write_only` no decode e avisar no `io_read` quando a leitura for 0.
- Permitir decodificar um valor conhecido sem I/O (`io_read(addr, raw=...)`).

**Non-Goals:**
- Expor shadow state de registradores write-only no emulador (follow-up, se necessário).
- Cobrir efeitos 3D/GXFIFO ou registradores além de vídeo 2D.
- Mudar o formato do schema existente.

## Register map (engine A = `0x04000000`, B = `0x04001000`)

| Offset | Register | Size | Fields |
|---:|---|---:|---|
| `0x10+2i` | `BG{i}HOFS` | 2 | `offset` (0..8) |
| `0x12+2i` | `BG{i}VOFS` | 2 | `offset` (0..8) |
| `0x40` | `WIN0H` | 2 | `right` (0..7), `left` (8..15) |
| `0x42` | `WIN1H` | 2 | `right` (0..7), `left` (8..15) |
| `0x44` | `WIN0V` | 2 | `bottom` (0..7), `top` (8..15) |
| `0x46` | `WIN1V` | 2 | `bottom` (0..7), `top` (8..15) |
| `0x48` | `WININ` | 2 | `win0_bg0..3`, `win0_obj`, `win0_effect`; `win1_*` (8..13) |
| `0x4A` | `WINOUT` | 2 | `out_bg0..3`, `out_obj`, `out_effect`; `objwin_*` (8..13) |
| `0x4C` | `MOSAIC` | 2 | `bg_h` (0..3), `bg_v` (4..7), `obj_h` (8..11), `obj_v` (12..15) |
| `0x50` | `BLDCNT` | 2 | `target1_*` (0..5), `effect` (6..7), `target2_*` (8..13) |
| `0x52` | `BLDALPHA` | 2 | `eva` (0..4), `evb` (8..12) |
| `0x54` | `BLDY` | 2 | `evy` (0..4) |

`i = 0..3`. Os registradores `BGxHOFS/VOFS`, `WIN0/1H/V`, `WININ`, `WINOUT`, `MOSAIC`,
`BLDCNT`, `BLDALPHA` e `BLDY` são **write-only** no hardware; `DISPCNT`/`BGxCNT` já são
R/W. O `MASTER_BRIGHT` já existe.

## Decisions

### 1. `write_only` no modelo

`Register` e `DecodedRegister` ganham `write_only: bool = False`; `Register.decode` propaga
o valor. `reg_dict` inclui `write_only`. O `io_read` adiciona um `hint` quando
`write_only && raw == 0` (“registrador write-only; leitura pode ser 0; use raw=...”).

**Alternativa:** esconder registradores write-only; descartado — o agente precisa saber que
existem e por que o valor é 0.

### 2. Decode puro por valor

`io_read(addr, raw=None)`: com `raw`, o MCP decodifica o valor sem ler memória (novo método
`IoReader.decode`); sem `raw`, mantém a leitura pelo debugger. Isso torna o schema útil para
savestates/logs e para write-only.

### 3. Bitfields

- `BGxHOFS/VOFS`: `offset` 9 bits (0..511).
- `WINxH`: `right`/`left`; `WINxV`: `bottom`/`top`.
- `WININ/WINOUT`: enums de enable por BG/OBJ/efeito; `WINOUT` tem o bloco da OBJ window.
- `MOSAIC`: quatro tamanhos de 4 bits.
- `BLDCNT`: alvos 1º/2º + modo (`none`, `alpha`, `white`, `black`).
- `BLDALPHA`: EVA/EVB 5 bits; `BLDY`: EVY 5 bits.

### 4. Sem emulador neste change

O melonDS pode não expor shadow state; o change documenta e sinaliza. Se o smoke mostrar que
os valores nunca são legíveis, um follow-up pode expor `video.regs` no canal de controle.

## Risks / Trade-offs

- [Write-only lê 0] → `write_only` + `hint`; decode puro via `raw=`.
- [Endereços/bitfields divergentes] → validar com GBATEK e valores sintéticos.
- [Schema maior] → 36 registradores novos; decode continua O(1).
- [Cliente antigo] → campos novos são aditivos; `io_read(addr)` continua igual.

## Migration Plan

Aditivo. Atualizar `mcp-io-decode` e testes. Rodar `pytest`, `pyright`, `lint-imports` e
`openspec validate --strict`; smoke real na engine B (scroll/janela/blend) e checar o hint
de write-only.

## Open Questions

- Expor shadow state no canal de controle (`video.io_state`) para write-only? (Follow-up.)
- Incluir `WINOBJ`/`BLDCNT` bits de backdrop como enums nomeados? (Sim, no schema.)
