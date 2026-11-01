## Context

Ver `proposal.md` — Why. O frontend Qt já tem diálogos de debug (`RAMInfoDialog`,
`ROMInfoDialog`) e a janela principal cria o menu System. O núcleo expõe `GPU.OAM` (2 KB,
engine A no offset 0 e B em `0x400`), `GPU.Palette` (2 KB; OBJ A em `0x200`, OBJ B em `0x600`)
e `GPU2D::GetOBJVRAM` (ponteiro/máscara do OBJ VRAM por engine). `GPU2D::DispCnt` dá o
mapeamento 1D/2D e o boundary.

## Goals / Non-Goals

**Goals (POC):**
- Janela OAM read-only, engine A/B, grid de 128, detalhes GBATEK e preview.
- Decodificar 4bpp/8bpp, 1D/2D, paleta OBJ padrão e transparência.
- Freeze para inspeção estável; sem custo com a janela fechada.

**Cobertura GBATEK implementada no POC:**
- Attr0/1/2 (`lcdobjoamattributes`, `dsvideoobjs`), shape×size, X/Y, priority, palette
  bank e bits de mosaic/affine/double-size (os flips aparecem nos detalhes, mas não são
  aplicados no preview).
- 4bpp/8bpp, transparência do índice 0 e paleta OBJ padrão (`lcdobjoamattributes`,
  `lcdcolorpalettes`).
- 1D/2D mapping (`lcdobjvramcharactertilemapping`; DISPCNT bit4 e bits20-21).
- Parâmetros R/S e A-D, R/S Address e double-size (`lcdobjoamrotationscalingparameters`).

**Lacunas de hardware documentadas no GBATEK (ainda NÃO implementadas no POC):**
- **Bitmap OBJ** (`mode=3`): `dsvideoobjs` (15-bit direct + alpha, DISPCNT bits 5/6/22,
  attr2 alpha). O POC mostra `BM`.
- **Rotação/escala affine**: `lcdobjoamrotationscalingparameters`; o POC só desenha o sprite
  reto + caixa double-size.
- **Extended palettes**: `dsvideoextendedpalettes` (DISPCNT bit31, VRAM F/G/I, 4096 cores).
- **Mosaic e alpha/color effects**: `lcdiomosaicfunction` (MOSAIC 0x0400004C) e
  `lcdiocolorspecialeffects` (BLDCNT/BLDALPHA; OBJ semi-transparente).

**Lacunas de UI/arquitetura (NÃO são especificadas pelo GBATEK):**
- Sem escrita/edição de OAM, cross-jump para tile/VRAM/paleta/disassembly, overlay na tela,
  filtro “usados”/ordenação/diff, dirty tracking, duas previews/zoom/export PNG.
- Leitura live (com Freeze) em vez de snapshot pela fila da EmuThread; sem persistência de
  geometria/engine; validação com gdb haltada pendente.
- Matriz visual 2D×8bpp: lacuna de **teste**, não de formato (o decoder já cobre 1D/2D e
  4/8bpp).

**Lição de regressão (2026-10-31):** o POC que funcionava usava `GetOBJVRAM` (buffer flat
populado pelo renderer) e passo de tile `bytes`. Ao adicionar as lacunas do GBATEK, troquei
para passo `boundary`, leitura pela bus da CPU e um renderer genérico para todos os sprites;
isso quebrou **todos** os sprites normais. Regra: o renderer normal fica intocado; modos
novos entram em funções separadas, com teste sintético controlado e PR próprio.

## Decisions

- **Frontend-only.** Nada no núcleo; o viewer lê `GPU.OAM`/`Palette`/`GetOBJVRAM` e
  `GPU2D::DispCnt`. Alternativa: expor via control channel — mais latência e não atende ao
  humano.
- **Timer de 100 ms** enquanto a janela está visível; para no `closeEvent`/destrutor.
- **Freeze via `EmuThread::emuPause/emuUnpause`.** O par é balanceado; se o usuário já pausou,
  o pause stack preserva. Sem freeze, a leitura é live (POC).
- **Decode GBATEK direto no frontend.** `attr0/1/2`, shape×size, 1D/2D, 4/8bpp, banco de
  paleta, double-size e R/S. Mantém o POC autocontido; extrair um decoder testável é follow-up.
- **Um único preview** para caber no POC; duas previews/zoom fino ficam para o H1/H3.

## Risks / Trade-offs

- [Leitura live concorrente com a EmuThread] → o POC oferece Freeze; a versão definitiva deve
  snapshotar via fila da EmuThread.
- [VRAM mapping muda em runtime] → `GetOBJVRAM` devolve o ponteiro/máscara atual; extended
  palettes ainda não.
- [Affine/bitmap confundidos com bug] → a UI mostra `BM`/caixa tracejada e este documento
  lista as limitações.
- [GDB halt + Freeze] → o par pause/unpause é o mesmo usado pela UI; validar em sessão com gdb.

## Migration Plan

Aditivo, frontend-only. A ação System → OAM viewer é habilitada quando há cartucho. Sem a
janela aberta, custo zero. O build é o mesmo; não há mudança de savestate/ROM.

## Open Questions

- Quando extrair o decoder para um módulo testável (H1/H3)?
- Cross-jump para o futuro tile/palette viewer entra no H1 ou H2?
