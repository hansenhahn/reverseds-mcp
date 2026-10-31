## Why

Hoje o NitroFS/overlays do MCP são montados a partir de um **caminho fixo de ROM**
(`RE_MCP_ROM` + bind-mount), que pode **divergir** do jogo carregado no emulador. Isso já
aconteceu na prática: o MCP mapeava offsets com a ROM do KH enquanto o melonDS rodava Hotel
Dusk, produzindo caminhos inexistentes. O **emulador é a fonte da verdade** de qual ROM está
carregada; o MCP deve ler exatamente essa ROM pelo canal de controle.

## What Changes

- Canal de controle: novos métodos `rom.info` (identidade do cartucho carregado) e
  `rom.read(offset, size)` (bytes da ROM carregada, via frame binário).
- MCP: `CartFs`/overlays passam a ler a ROM **via canal**; o adaptador de arquivo e a config
  `RE_MCP_ROM`/bind-mount são removidos.
- Nova tool `rom_info` para o agente confirmar qual ROM está em execução.
- O MCP detecta troca de ROM (nome/tamanho/gamecode/checksum) e remonta o FS automaticamente.
- Deploy/docs/smoke deixam de depender de `docker-compose.rom.yml`.

## Capabilities

### Modified Capabilities
- `control-channel`: expõe a ROM carregada (`rom.info`) e seus bytes (`rom.read`).
- `cartfs`: interpreta o filesystem da ROM carregada no emulador, via canal.
- `nds-overlays`: interpreta as tabelas de overlay da ROM carregada, via canal.
- `mcp-re-workflows`: usa a ROM em execução como fonte da verdade e expõe `rom_info`.

## Impact

- Emulador (fork): `ControlServer` (métodos `rom.info`/`rom.read`); `EmuInstance` (acesso
  thread-safe ao nome/caminho da ROM carregada).
- MCP: `infra/ndsrom.py` (adaptador via canal), `bridge.py`, `config.py`, tools de cartucho,
  testes e docs.
- Deploy: remove o override de ROM; `RE_MCP_ROM` deixa de existir.
