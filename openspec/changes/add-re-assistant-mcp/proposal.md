## Why

Queremos um agente de IA que ajude a **fazer engenharia reversa** de jogos de NDS:
observar o jogo, achar o código que lê/escreve um dado, acompanhar carregamento de
assets e atuar como copiloto. O melonDS já expõe os canais necessários (controle e
GDB), mas nada disso está no formato que um agente consome. Este change define o
**MCP de engenharia reversa assistida**.

## What Changes

- Um servidor **MCP** (dentro de `reverse-ds`) que liga **dois backends** do
  melonDS: o **canal de controle** (JSON-RPC: input, tela, savestate, pause, cart
  trace) e o **gdb** (que fala RSP com o stub: memória, registradores,
  breakpoints, watchpoints, run/step).
- Expõe **tools** ao agente, agrupadas em: emulação, depuração e **workflows de
  RE** (ex.: `find_writer`/`find_reader`).
- **Função central**: traduzir as **leituras do cartucho (SPI/ROM)** em **arquivos
  NitroFS** (via **FAT/FNT**) — transformar o trace bruto em "quais arquivos o
  jogo leu".
- Resolve endereço ↔ símbolo (`.map`).
- **Não modifica o emulador** — apenas consome os canais existentes.

## Capabilities

### New Capabilities
- `mcp-bridge`: conexão e ciclo de vida dos backends (control socket + GDB stub),
  configuração e erros.
- `mcp-control-tools`: tools de emulação (input, tela, savestate, pause, cart trace).
- `mcp-debug-tools`: tools de depuração (memória, registradores, breakpoints,
  watchpoints, run/step).
- `mcp-re-workflows`: workflows de RE assistida (find_writer/reader, diff de
  estado, símbolos, NitroFS).

### Modified Capabilities
<!-- nenhuma -->

## Impact

- **Novo projeto** dentro de `reverse-ds` (servidor MCP; provavelmente Python).
- **Consome** os canais já existentes do melonDS — **nada muda no emulador**.
- **Depende** dos specs `control-channel` e `cart-trace`, e do stub GDB (RSP).
- **Futuro**: integração com Ghidra (decompilação/xrefs) como backend de análise
  estática — fora de escopo agora.
