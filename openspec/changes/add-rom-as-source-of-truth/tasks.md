## 1. Emulador — canal de controle

- [x] 1.1 Adicionar `rom.info` (loaded/name/path/size/gamecode/checksum) ao `ControlServer`, com checksum cacheado por cartucho. Verificar: build OK e chamada manual no socket devolve os campos.
- [x] 1.2 Adicionar `rom.read(offset, size)` com validação de limites e frame binário (limite de 16 MiB). Verificar: leitura de um offset conhecido devolve os bytes esperados e uma leitura fora dos limites retorna erro.
- [x] 1.3 Expor nome/caminho da ROM de forma thread-safe no `EmuInstance` (mutex próprio). Verificar: build OK e `rom.info` reflete o nome do arquivo aberto.
- [x] 1.4 Compilar o fork do melonDS. Verificar: `cmake --build` sem erros.

## 2. MCP — adaptador via canal

- [x] 2.1 Trocar `NdsRom` (arquivo) por `ChannelRom` (canal) mantendo o parse no domínio. Verificar: testes unitários com canal fake.
- [x] 2.2 Remover `RE_MCP_ROM`/`rom_path` do `Config` e o adaptador de arquivo. Verificar: `rg RE_MCP_ROM` sem referências no MCP; `pyright` limpo.
- [x] 2.3 Detectar troca de ROM por identidade e remontar FS/overlays. Verificar: teste com fake que muda a ROM entre chamadas.
- [x] 2.4 Adicionar a tool `rom_info` e fazer as tools de cartucho usarem a ROM do emulador. Verificar: `list_tools` contém `rom_info`; tools retornam erro claro quando o emulador/canal não responde.
- [x] 2.5 Mapear erros de canal nas tools de cartucho para `{"error", "hint"}`. Verificar: teste unitário do caminho de erro.

## 3. Deploy, docs e smoke

- [x] 3.1 Remover `docker-compose.rom.yml`, `MCP_COMPOSE_EXTRA` e menções a `RE_MCP_ROM` no deploy/docs. Verificar: `rg RE_MCP_ROM` e `rg docker-compose.rom` sem referências (exceto histórico).
- [x] 3.2 Atualizar `smoke/harness.py` para não passar `RE_MCP_ROM` e adicionar caso de smoke de ROM (`rom_info`, `cart_list`, `cart_file`, `cart_read`). Verificar: caso adicionado; smoke manual equivalente validado (`rom_info`, `cart_list`, `overlay_list`).
- [x] 3.3 Atualizar o ROADMAP marcando a feature como feita. Verificar: seção atualizada.

## 4. Validação

- [x] 4.1 `uv run pyright`, `uv run lint-imports` e `uv run python -m pytest` no MCP. Verificar: sem erros.
- [x] 4.2 `openspec validate add-rom-as-source-of-truth --strict`. Verificar: sem erros.
- [x] 4.3 Smoke E2E com ROM real usando a ROM servida pelo emulador (feito com `xpa-khe.nds`; a feature é agnóstica de ROM). Verificar: `rom_info` e `cart_*` coerentes com a ROM aberta.

> Validado em 2026-10-30: build do emulador com `-j 1`; `rom.info`/`rom.read` (limite e
> bounds) OK; MCP `pytest` (111), `pyright`, `lint-imports` e `openspec validate --strict`
> verdes; smoke real com `xpa-khe.nds` (1596 arquivos, 303 overlays ARM9, overlay 22 em
> `0x02082960`).
