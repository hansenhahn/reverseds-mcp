## Why

`render_layer` mostra só a janela visível de 256×192. HUDs/mapas de menu costumam usar o
**mapa BG virtual inteiro** (256/512/1024), e o agente hoje só consegue inspecionar célula a
célula (`map_cell`) ou a janela renderizada. Falta um dump/composição do mapa completo.

## What Changes

- Nova tool `dump_tilemap(engine, bg)`:
  - varre o mapa virtual inteiro (text ou affine);
  - grava um JSON em `/out` com `cell_x/y`, `entry`, `tile_index`, `tile_addr`, `palette`,
    `flip_h/v`, `bpp`;
  - devolve caminho + dimensões/contagem.
- Nova tool `render_bg_map(engine, bg)`:
  - compõe o mapa virtual inteiro em PNG (4/8bpp, text/affine, flips);
  - lê a paleta BG do engine (`0x05000000` / `0x05000400`);
  - devolve caminho + dimensões/contagem.
- Domínio: `BgLayer.palette_base` e decodificação de tile 4/8bpp (`tile_indices`), conversão
  BGR555→RGB.
- Leituras de mapa/tiles/paleta em **bulk** (1 leitura por região), não uma por célula.
- Text e affine (mapa plano); extended/bitmap/3D retornam erro claro.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-re-workflows`: dump e composição do mapa BG completo (text/affine).

## Impact

- MCP: `domain/display.py`, `application/display.py`, `tools/re.py`, testes.
- Emulador: **nenhuma mudança**.
- Artefatos: PNG/JSON em `RE_MCP_OUT_DIR` (`/out`).
