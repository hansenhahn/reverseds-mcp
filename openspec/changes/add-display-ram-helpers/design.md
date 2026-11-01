## Context

Ver `proposal.md` — Why. `video_state` já lê DISPCNT/BGxCNT; `read_vram` lê VRAM; o DMA trace
decodifica `src/dst/cnt/pc`. O elo display→RAM não existe.

## Goals / Non-Goals

**Goals:**
- Resolver célula BG → tile/entrada/endereço/paleta.
- Ler bytes de tile BG/OBJ e achá-los na RAM.
- Dado um endereço de VRAM, listar DMAs que escreveram nele.

**Non-Goals:**
- BG **extended**/bitmap/3D no `map_cell` (só text/affine nesta versão).
- Varredura da RAM além de 4 MiB ou de shared WRAM/VRAM.
- Correlação inversa “tile→todos os DMAs históricos” (a janela é ao vivo).
- Alterações no emulador.

## Decisions

- **Usar bits crus do DISPCNT/BGxCNT.** O decoder de `video_state` usa layout GBA-like para
  alguns bits do DISPCNT; os helpers leem `decoded.raw` e aplicam as regras NDS do GBATEK
  (bit4 OBJ 1D, bits20-21 boundary, bits24-26 char base, bits27-29 screen base).
- **Text + affine.** Text: entrada 16-bit, blocos 256×256; affine: entrada 8-bit linear.
  Extended/bitmap/3D retornam erro claro.
- **Tile address BG:** `char_base + tile * (32/64)`; char/screen base incluem a janela da
  engine (0x06000000/0x06200000).
- **OBJ:** 1D (`tile * boundary`) ou 2D (`(tile & mask)*bytes + (tile >> shift)*0x400`),
  com `bpp` 4/8.
- **`find_tile_in_ram`:** lê até 4 MiB de `0x02000000`, busca o padrão de 32/64 bytes e limita
  a 32 ocorrências. Alternativa: indexar todo o dump; caro e desnecessário.
- **`dma_source`:** usa `DmaTrace.find_destination`, que inicia/coleta/para o trace e filtra
  pela faixa de destino (`inc`/`dec`/`fixed`). O `stop` roda em `finally`.
- **Sem emulador.** Tudo sobre portas existentes.

## Risks / Trade-offs

- [Decode de BGxCNT/dispcnt] → usa bits crus; o `video_state` não é fonte para os campos NDS.
- [Leitura de RAM 4 MiB] → operação on-demand; pode custar ~1s via gdb.
- [DMA ao vivo] → só pega transfers durante a janela; para uma transição, o agente pode usar
  `dma_trace_start` + input + `dma_trace_read`.
- [Overlays/VRAM mapping] → os endereços usam as janelas padrão; mapping de VRAM fora do
  padrão ainda não é remapeado.
- [Tile patterns curtos] → 32/64 bytes podem ter falsos positivos; retorna todos (limitado).

## Migration Plan

Aditivo; novas tools e módulos. Validar com `pytest`, `pyright`, `lint-imports` e
`openspec validate --strict`; smoke real opcional.
