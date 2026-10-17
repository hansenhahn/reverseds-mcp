## 1. Emulador — captura pausada (frontend)

- [ ] 1.1 Render sob demanda do quadro atual na `EmuThread` (caminho de captura), sem depender do passo de quadro. Verificar: com a CPU parada, a captura devolve pixels (não expira).
- [ ] 1.2 Reuso do renderer existente (`GetFramebuffers`); sem trabalho por quadro adicional. Verificar: captura não pausada continua funcionando.

## 2. MCP — ajuste de comportamento

- [ ] 2.1 A tool de captura deixa de tratar "CPU parada" como erro (remove o hint enganoso). Verificar: captura com gdb conectado/CPU parada retorna imagem.
- [ ] 2.2 Smoke: congelar um frame e capturá-lo; mesmo frame entre duas capturas. Verificar: PNGs idênticos.

## 3. Validação

- [ ] 3.1 Build do melonDS sem regressão; testes/smoke do MCP verdes. Verificar: build + `pytest`.
- [ ] 3.2 `openspec validate add-paused-capture --strict` OK. Verificar: comando sem erro.
