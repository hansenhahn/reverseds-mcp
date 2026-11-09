## Why

Sessões de RE precisam **trocar o conteúdo de um arquivo NitroFS em runtime** (ex.:
`/mi/wd/wd_tt`) para testar assets sem repack da ROM e sem write de RAM. O write de RAM via
GDB está quebrado neste build (pacote `X` derruba o emulador) e o repack a cada iteração é
lento e arriscado. Servir o arquivo alterado pelo próprio loader do jogo contorna ambos.

## What Changes

- **Emulador**: overrides por **range absoluto da ROM** aplicados no ponto único de leitura de
  dados do cartucho (`CartCommon::ROMRead32`), cobrindo **CPU e DMA**. Um arquivo do host é
  servido no lugar dos bytes originais, com hot reload e contadores; sem override ativo, o
  caminho original permanece intacto.
- **Canal de controle**: métodos `cart.override.set`, `cart.override.clear`,
  `cart.override.list`, `cart.override.reload` e `cart.override.stats`. O `host_path` é lido
  pela thread do controle (nunca pela EmuThread).
- **MCP**: resolução `path` NitroFS → `[rom_start, rom_end)` usando o parser FNT/FAT já
  existente; serviço de aplicação e tools `cart_override_set/clear/list/reload/stats`.
- **Semântica de tamanho**: arquivo do host maior → excedente ignorado; menor → zero-fill.
- `rom.read` continua servindo a **imagem original** da ROM (extração não é afetada).
- Overrides **não entram em savestate** e são descartados na troca/ejecção do cartucho.

## Capabilities

### New Capabilities
- `cart-override`: comportamento de override de conteúdo do cartucho em runtime (servir bytes
  em leituras CPU/DMA, zero-fill, hot reload, contadores, ciclo de vida).

### Modified Capabilities
- `control-channel`: novos métodos `cart.override.*` (parâmetros, erros, thread-safety).
- `mcp-re-workflows`: tools `cart_override_*` resolvendo path NitroFS → range.

## Impact

- **melonDS**: `src/NDSCart/CartCommon.{h,cpp}` (API de override + hook de leitura);
  `src/frontend/qt_sdl/ControlServer.{h,cpp}` (comandos e leitura do arquivo do host).
  `rom.read`/`Checksum()` não mudam.
- **MCP**: `application/ports/cartfs.py` e `infra/ndsrom.py` (`span(path)`);
  `application/cart_override.py` (novo), `bridge.py`, `tools/cart_override.py`,
  `tools/server.py`, testes e docs.
- **Deploy**: `host_path` é resolvido pelo processo do **emulador**; em contêiner, precisa
  estar visível no mesmo filesystem/container.
