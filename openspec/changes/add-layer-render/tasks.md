## 1. Emulador — render de camada (frontend)

- [ ] 1.1 Render de uma camada isolada (engine × BG0-3/OBJ/3D) reusando o renderer de software. Verificar: render de OBJ do engine B devolve imagem não-vazia no frame do slot3.
- [ ] 1.2 Validar a combinação engine×camada e reportar erro claro para inválidas. Verificar: `BG0` 3D no engine B → erro.

## 2. MCP — tool

- [ ] 2.1 Tool `render_layer(engine, layer)` que pede o render e salva o quadro em `/out`. Verificar: agente lista a tool e obtém um PNG.
- [ ] 2.2 Smoke: `render_layer(B, obj)` e `render_layer(A, 3d)` no frame do slot3; comparar com a captura. Verificar: o conteúdo aparece na camada esperada.

## 3. Validação

- [ ] 3.1 Build do melonDS sem regressão; testes/smoke do MCP verdes. Verificar: build + `pytest`.
- [ ] 3.2 `openspec validate add-layer-render --strict` OK. Verificar: comando sem erro.
