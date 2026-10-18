## Why

A VRAM é preenchida por **DMA**, e watchpoint de CPU **não captura DMA** (descoberta da
sessão). Sem um trace de DMA, não há como ligar o upload de um asset à VRAM ao **código
que o disparou** (`PC` que programou o canal). É o elo que falta entre "o texto está nesta
VRAM" e "qual código o colocou lá".

## What Changes

- **Trace de DMA**: no início de cada transferência, registrar um item **decodificado**: o
  canal, o **de → para** (`src`/`dst` + controles de origem/destino), o `length` em **bytes**
  e o **controle decodificado** do `DMAxCNT` — pelos **mesmos nomes do schema GBATEK**
  (`transfer_32bit`, `src_control`/`dest_control`, `start_timing`, `repeat`, `irq`,
  `enable`) — mais o `pc` que programou o canal.
- O item **reusa a decodificação de IO do `add-io-decode`** (`domain/io`, schema
  `registers/dma.py`, o mesmo do `io_read`) — **não** expõe `cnt` como bits crus.
- Entrega em **lotes** (por N itens ou timeout), como o cart trace; **subscrição**
  (start/read/stop).
- Opcional: breakpoint em IO (`0x040000B0+`) e watchpoint de IO (reuso dos primitivos já
  existentes).
- Emulador (fork) + tools MCP (iniciar/ler/parar).
- **Não altera o comportamento de emulação**; sem assinante, sem custo.

## Capabilities

### New Capabilities
- `dma-trace`: trace das transferências de DMA.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- melonDS: hook no início do DMA (núcleo), seguindo o padrão do `cart-trace` (flag
  `O(1)`/sem alocação na EmuThread; batching e envio fora dela).
- MCP: tools de trace análogas às do cartucho.
