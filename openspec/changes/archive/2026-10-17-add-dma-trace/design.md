## Context

Ver `proposal.md` — Why. O fork já tem o `cart-trace` (hook no início da transferência,
batching por N/timeout, `eventfd`/notificação, envio fora da EmuThread) — o padrão a
reusar. O DMA ocorre no **núcleo** (`src/NDS.cpp`, funções de DMA por canal); o hook fica
no início da transferência, onde `src`/`dst`/`len`/`cnt` estão disponíveis e o `PC` do
programador pode ser capturado no momento da programação do canal.

## Goals / Non-Goals

**Goals:**
- Registrar cada DMA **decodificado** (canal, de→para, `length` em bytes, controle pelo
  schema GBATEK), em lotes, sem custo sem assinante.

**Non-Goals:**
- Trace de leitura de cartucho (já existe: `cart-trace`).
- Capturar o *conteúdo* transferido (só a descrição da transferência).

## Decisions

- **Reusar o padrão do `cart-trace`**: mesmo batching/entrega, para consistência e
  mínimo custo. Alternativa descartada: watchpoint de CPU na VRAM — não dispara em DMA
  (foi o que travou a sessão).
- **Ring de capacidade fixa (não um vetor crescente)**: o buffer é um **ring limitado**
  (`max_items`, default 65536); ao estourar, **descarta o mais antigo** e conta os
  descartados (O(1), sem alocação na EmuThread). Alternativa descartada: vetor que cresce —
  risco de **memória sem teto** se o leitor atrasar. (Aplicado também ao `cart-trace`, que
  tinha o mesmo problema.)
- **Item decodificado — reuso do `add-io-decode`**: o item é um value object de domínio
  (`DmaTransfer`) que expressa **de → para** (`source`/`destination` + controles de
  endereço), `length` em **bytes** e o **controle decodificado** pelo schema GBATEK
  (`domain/io`, `registers/dma.py`, o mesmo do `io_read`) — **não** `cnt` cru. O emulador
  emite a descrição crua (canal/`src`/`dst`/`cnt`/`pc`); a **decodificação** fica no MCP, no
  domínio. Completar `DMAxSAD`/`DMAxDAD` no schema (hoje só há `DMAxCNT`).
  Alternativa descartada: expor bits crus — repetiria a decodificação que já temos (viola
  DRY) e obrigaria o agente a decodificar bits na mão.
- **Hook no início do DMA** (núcleo) — único ponto que vê a transferência e o `PC`
  programador. Alternativa descartada: breakpoint em IO (`0x040000B0+`) — vê a
  programação, não a transferência (e é opcional/complementar).
- **`PC` do programador** capturado quando o canal é programado (registradores de IO),
  não no momento da transferência (que pode ser por timing/vblank).

## Risks / Trade-offs

- [Tocar o núcleo] → justificado: só o núcleo vê o DMA; o hook é O(1)/sem alocação e
  segue o precedente do `cart-trace`. Não altera a emulação.
- [`PC` programador vs momento da transferência] → registrar o `PC` no write dos
  registradores do canal; se indisponível, cair para o `PC` no início da transferência.
