## Context

As leituras de ROM do cartucho têm dois caminhos que convergem num **início de
transferência** com endereço/tamanho conhecidos: o comando AUXSPI
(`CartCommon::ROMCommandStart`) e o ROMCNT/cart DMA
(`NDSCartSlot::Interface::WriteROMCnt`, que calcula o `datasize` e chama
`ROMCommandStart`). O canal de controle já existe (JSON-RPC sobre Unix socket,
com o padrão de batching/streaming da captura de tela). Ver `proposal.md` para a
motivação.

## Goals / Non-Goals

**Goals:**
- Registrar **todas** as leituras por transferência, sem perda.
- Entregar em lotes por **N ou timeout**, sem floodar o canal.
- Hook mínimo no núcleo; custo zero quando desabilitado.

**Non-Goals:**
- Mapear offset→arquivo **NitroFS** (o consumidor já domina).
- Capturar leituras por palavra (`ROMRead32`) — granularidade fina demais.
- Ler o cartão SD/NAND (DSi) nesta versão.

## Decisions

### D1. Hook no início da transferência
**Decisão**: registrar no ponto de transferência — `WriteROMCnt` no start (dá o
`datasize`) combinado com `ROMCommandStart` (dá o endereço/comando).
**Por quê**: é o menor volume possível (uma transferência lê até 16 KB) e já tem
endereço+tamanho. Uma transferência = um item.
**Alternativas**: hook por palavra (`ROMRead32`) — rejeitado (milhões/s); hook só
no comando AUXSPI — perde o caminho do ROMCNT/DMA.

### D2. Batching com double-buffer; flush na thread do cliente
**Decisão**: um buffer pré-alocado recebe os itens na EmuThread (append O(1)); ao
atingir N, a EmuThread **sinaliza** via um `eventfd` do assinante. O flush roda na
**thread do próprio cliente assinante** (o `poll` dela já tem timeout): ela drena
o buffer (swap) e envia. O timeout vive nessa thread, **não** na EmuThread.
**Por quê**: zero alocação e zero checagem de tempo na EmuThread; evita uma thread
extra e o problema de tempo de vida do `Client` (o flush é na própria thread que
atende o cliente). Funciona mesmo com o emulador **pausado**.
**Alternativas**: thread "pump" dedicada — mais uma thread e risco de `Client*`
pendurado; checar timeout no tick da EmuThread — acopla ao frame rate e não
dispara pausado; item a item (flood); ring buffer (perde dado).

### D3. Subscrição (opt-in) com entrega em lote
**Decisão**: desligado por padrão. `cart.trace.start {batch, timeout_ms}`
**subscreve**; `cart.trace.stop` **cancela**. **Um trace ativo por vez**; o
servidor empurra lotes como notificações (`event.cart`) ao assinante. Cada lote
traz os itens e um contador.
**Por quê**: assim o agente monitora só **casos específicos** (liga/desliga à
vontade), e o trace é **já agregado** (um lote) — então push é adequado,
diferente do push por quadro, descartado antes. Sem assinante, custo zero.
**Alternativas**: só poll/drain (`cart.drain`) — viável, mas o push de lotes dá o
"tempo real" que o caso pede.

### D4. Sem perda — crescer ou sinalizar overflow
**Decisão**: o buffer cresce conforme necessário até um limite alto; ao atingir o
limite, o lote entregue inclui um marcador de **overflow** — nunca descarta em
silêncio.
**Por quê**: leituras são informação valiosa (requisito explícito).

### D5. Conteúdo do item
**Decisão**: item = `{addr, len, cmd}`. Para comandos de leitura (ex.: `0xB7`), o
endereço é extraído do comando; para outros, registra-se o comando com endereço
irrelevante.
**Por quê**: dá endereço+tamanho por leitura e mantém o comando para inspeção.

### D6. NitroFS fora de escopo
**Decisão**: entregar offset cru; o mapeamento para arquivo é do consumidor.

## Risks / Trade-offs

- **Backpressure** (cliente lento, buffer crescendo) → *Mitigação*: limite alto +
  marcador de overflow; nunca bloqueia a EmuThread.
- **Caminhos específicos do DSi** (SD/NAND) não cobertos → *Mitigação*:
  documentar como non-goal; estender depois reaproveitando o mesmo hook.
- **Decodificação do comando** duplicada no hook → *Mitigação*: reaproveitar o
  endereço já calculado em `ROMCommandStart` em vez de reparsear.
