## 1. Emulador — hook de DMA (núcleo, seguindo o cart-trace)

- [ ] 1.1 Hook no início de cada DMA: capturar `src`/`dst`/`length`/`cnt` (O(1), sem alocação) e o `pc` programador. Verificar: um DMA gera um item; sem assinante não há custo.
- [ ] 1.2 Batching por N/timeout e notificação fora da EmuThread (reuso do padrão do cart-trace). Verificar: lotes chegam completos ao cliente.
- [ ] 1.3 Métodos no canal de controle: `dma.trace.start`/`dma.trace.stop` (+ entrega por evento). Verificar: `control-client.py` inicia, roda e recebe itens.

## 2. MCP — tools

- [ ] 2.1 Tools `dma_trace_start`/`dma_trace_read`/`dma_trace_stop` (análogas às de cartucho). Verificar: agente lista as tools.
- [ ] 2.2 Smoke: rodar a intro e mostrar DMAs para a VRAM (dst em 0x06000000+) com o `pc`. Verificar: há itens de DMA para VRAM durante o START→intro.

## 3. Validação

- [ ] 3.1 Build do melonDS sem regressão; testes/smoke do MCP verdes. Verificar: build + `pytest`.
- [ ] 3.2 `openspec validate add-dma-trace --strict` OK. Verificar: comando sem erro.
