## 1. POC implementado

- [x] 1.1 Criar `OAMViewerDialog` (Qt) e ação **System → OAM viewer**, com inclusão no
  CMake. Verificar: build inclui o arquivo e a ação aparece com cartucho.
- [x] 1.2 Grid 16×8 de 128 slots por engine A/B, thumbnail, hachura nos livres e destaque do
  selecionado. Verificar: visual no menu de status do KH.
- [x] 1.3 Detalhes GBATEK: No., X/Y, Size, OAM Data, OAM Address, Tile Address, Mode/Type,
  Palette, Priority, Flip, Mosaic, Rot/Scal, A-D e R/S Address. Verificar: campos coerentes
  para um OAM selecionado.
- [x] 1.4 Preview ampliado com bounding box; affine double-size mostra caixa tracejada.
  Verificar: sprite e dimensões corretos.
- [x] 1.5 Freeze (pause/unpause balanceado), timer de 100 ms e parada ao fechar. Verificar:
  congelar mantém o viewer atualizando e fechar restaura a execução.
- [x] 1.6 Decodificar 4bpp/8bpp, 1D/2D, paleta OBJ padrão e transparência (índice 0).
  Verificar: thumbnails do menu de status.
- [x] 1.7 Build do fork (`-j 1`) e teste manual com `xpa-khe.nds` no menu de status.
  Verificar: janela abre, engine B mostra OAMs, detalhes/preview coerentes.

## 2. Limitações conhecidas (POC) — follow-ups

- [ ] 2.1 Renderizar **bitmap OBJ** (`mode=3`, 15-bit + alpha) em vez de mostrar `BM`.
- [ ] 2.2 Rotacionar/escalar sprites **affine** no preview (A-D), não só bounding box.
- [ ] 2.3 Suportar **extended palettes** (DISPCNT bit31) para OBJ.
- [ ] 2.4 Aplicar **mosaic** e alpha/color special effects no preview (ou indicar “raw”).
- [ ] 2.5 Escrita/edição de OAM (poke/drag) com confirmação explícita.
- [ ] 2.6 Cross-jump para tile/VRAM/palette e, depois, para o disassembly.
- [ ] 2.7 Overlay dos sprites na tela do jogo e filtro “usados apenas”/ordenação por prioridade.
- [ ] 2.8 Indicador de **dirty/refresh** por OAM (o que mudou desde o último frame).
- [ ] 2.9 Duas previews (zoom/1:1), zoom por pixel e export PNG.
- [ ] 2.10 Snapshot thread-safe via fila da EmuThread (hoje o POC lê live; Freeze evita tearing).
- [ ] 2.11 Extrair o decoder OAM→bitmap para módulo puro e cobrir com testes unitários
  (1D/2D, 4/8bpp, affine, bitmap).
- [ ] 2.12 Matriz visual 2D mapping × 8bpp em outros jogos; persistir geometria/engine.
- [ ] 2.13 Persistir/restaurar geometria da janela e engine selecionada (`QSettings`).
- [ ] 2.14 Validar Freeze com gdb anexado/haltado (pause stack e leitura).
- [ ] 2.15 Manter o renderer normal (`GetOBJVRAM` flat + passo `bytes`) **intocado**; modos
  novos em funções separadas, com teste sintético antes de integrar.
- [ ] 2.16 Aplicar `X-Flip`/`Y-Flip` no preview normal (hoje só aparecem nos detalhes).

## 3. Validação

- [x] 3.1 Build sem regressão e janela testada com ROM real.
- [ ] 3.2 Smoke visual com pelo menos outro jogo/engine e um sprite affine/bitmap real.
- [x] 3.3 PR do fork para a trilha H: **PR #16** (`feat/oam-viewer`), com o POC
  preservado. As lacunas do GBATEK ficam para PRs separados em cima dele.
