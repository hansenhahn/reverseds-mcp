## Why

O agente (MCP) precisa saber, em tempo real, **o que o jogo lê do cartucho** —
pra entender carregamento de assets, streaming e localizar dados. Hoje as
leituras de ROM passam por dentro do núcleo (`NDSCart`) e não são expostas.

## What Changes

- Adiciona um **trace de leitura do cartucho**: no início de cada transferência
  (AUXSPI / ROMCNT), o núcleo registra `{endereço, tamanho, comando}`.
- **Batching**: os registros são acumulados e entregues em lotes, por **N
  registros** ou por **timeout** — sem perder nenhum (não é ring buffer nem
  filtro).
- Exposição pelo **canal de controle**: iniciar/parar o trace com parâmetros
  (tamanho do lote, timeout) e receber os lotes.
- Hook **mínimo no núcleo** (`NDSCartSlot::Interface` / `CartCommon`); o trabalho
  pesado (bufferizar, serializar, enviar) fica **fora** da thread de emulação.
- Mapear offset→arquivo **NitroFS** fica **fora de escopo** (o consumidor já
  domina isso).

## Capabilities

### New Capabilities
- `cart-trace`: trace das leituras do cartucho, com batching por N/timeout,
  exposto pelo canal de controle.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- **Núcleo**: hook no início da transferência do cartucho
  (`NDSCartSlot::Interface::WriteROMCnt` no start, e `CartCommon::ROMCommandStart`
  para o endereço).
- **Frontend**: o `ControlServer` ganha os métodos de trace e o buffer de lote.
- **Performance**: desabilitado = zero custo; habilitado = append O(1) na
  EmuThread + sinal; I/O e serialização na thread de controle.
- **Relação**: complementa o canal de controle; **não** usa o sistema de eventos
  geral (descartado).
