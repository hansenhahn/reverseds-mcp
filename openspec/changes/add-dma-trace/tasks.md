## 1. Domínio — item decodificado (reuso do `add-io-decode`)

- [x] 1.1 Value object `DmaTransfer` (+ `DmaEndpoint`) decodificando o `DMAxCNT` pelo schema GBATEK `domain/io` (mesmos nomes do `io_read`); de→para com endereço+controle e `length` em bytes; teste unitário puro. (O `src`/`dst` vêm do próprio trace, então não foi preciso adicionar `DMAxSAD`/`DMAxDAD` ao schema.)

## 2. Emulador — hook de DMA (núcleo, seguindo o cart-trace)

- [x] 2.1 Hook no início de cada DMA: `OnDmaTransfer` chamado em `DMA::Start()` com `cpu`/`ch`/`src`/`dst`/`cnt`/`pc` (O(1), sem alocação); sem assinante (nullptr) não há custo.
- [x] 2.2 Batching por N/timeout e notificação por `eventfd` fora da EmuThread + **ring de capacidade fixa** (`max_items`, descarta o mais antigo e conta `dropped`). Verificado: com cap pequeno, `dropped>0` e lotes ≤ cap.
- [x] 2.3 Métodos no canal de controle: `dma.trace.start`/`dma.trace.stop` + notificação `event.dma`. Verificado com cliente direto.

## 3. MCP — tools

- [x] 3.1 Tools `dma_trace_start`/`dma_trace_read`/`dma_trace_stop` (análogas às de cartucho), decodificando cada item em `DmaTransfer`.
- [x] 3.2 Smoke: rodar a intro e mostrar DMAs para a VRAM — verificado (dst em `0x06400000`/`0x07000000`, com `pc` e controle decodificado).

## 4. Validação

- [x] 4.1 Build do melonDS sem regressão; `pyright`/`lint-imports`/`pytest` verdes.
- [x] 4.2 `openspec validate add-dma-trace --strict` OK. Verificar: comando sem erro.
