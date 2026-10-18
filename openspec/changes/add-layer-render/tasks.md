## 1. Emulador — render de camada (frontend)

- [x] 1.1 Render de uma camada isolada (engine × BG0-3/OBJ/3D) reusando o renderer de software, em **buffers isolados** (sem tocar no quadro exibido). Verificar: 3D do engine A devolve a cena 3D; OBJ do engine B devolve conteúdo.
- [x] 1.2 Validar a combinação engine×camada e reportar erro claro para inválidas. Verificar: `3d` no engine B → erro.

## 2. MCP — tool

- [x] 2.1 Tool `render_layer(engine, layer, screens, format)` que pede o render e salva os PNGs em `/out`. Verificar: agente lista a tool e obtém PNGs.
- [x] 2.2 Smoke: `render_layer(A, 3d)` e `render_layer(B, obj)`; o conteúdo aparece na camada esperada. Verificar: a camada `3d` do engine A devolve a cena 3D.

## 3. Validação

- [x] 3.1 Build do melonDS sem regressão; `pyright`, `lint-imports` e `pytest` verdes. Verificar: build + `pytest` (39) OK.
- [x] 3.2 `openspec validate add-layer-render --strict` OK. Verificar: comando sem erro.
