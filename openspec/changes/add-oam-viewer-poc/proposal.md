## Why

Hoje o copiloto humano depende do agente para `mem_dump_file`/`render_layer` e abrir arquivos
para “ver” a VRAM/OAM. Uma janela de **OAM viewer** no próprio melonDS (como a do no$gba) dá
inspeção visual imediata, sem round-trip com o MCP, e ajuda a guiar a sessão de RE. O H0 do
roadmap escolheu OAM como POC porque exercita o caminho `OAM → tile OBJ → paleta OBJ → bitmap`.

## What Changes

- Nova janela **System → OAM viewer** no frontend Qt do fork.
- Grid de 128 slots (16×8) por engine (A/B), com thumbnail; slots livres em hachura e o
  selecionado destacado.
- Painel de detalhes com os campos do GBATEK: No., X/Y, Size, OAM Data, OAM Address,
  Tile Address, OBJ Mode/Type, Palette, Priority, Flip, Mosaic, Rot/Scal, A-D e R/S Address.
- Preview ampliado com bounding box; affine double-size mostra a caixa tracejada.
- **Freeze** opcional (pausa a emulação) para inspeção estável; leitura **read-only**.
- Limitações do POC registradas explicitamente (bitmap OBJ, rotação affine, extended palettes,
  escrita, cross-jump etc.) para não serem confundidas com bugs.

## Capabilities

### New Capabilities
- `oam-viewer`: inspeção interativa de OAM/OBJ no frontend do emulador, por engine, com
  detalhes e preview, sem alterar o estado da emulação.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- Emulador (frontend Qt): `OAMViewerDialog.{h,cpp}` (novo), `Window.{h,cpp}` (menu/ação) e
  `CMakeLists.txt`.
- Núcleo: **nenhuma mudança**; lê `GPU.OAM`, `GPU.Palette` e `GetOBJVRAM`.
- MCP: **nenhuma mudança**.
- Custo zero com a janela fechada; refresh só enquanto visível.
