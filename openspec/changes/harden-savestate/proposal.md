## Why

Savestates falham silenciosamente justamente quando são mais necessários: com o debugger
anexado, `savestate.save`/`savestate.load` retornam `ok` mesmo quando o estado restaurado não é
o esperado (slot de letreiro carregou a cena da prisão). Os slots numéricos são compartilhados
com a UI, sem dono, lock nem metadados, então qualquer save externo sobrescreve o do agente
sem aviso. Não há verificação de integridade nem round-trip (frame/PC), e o MCP não sabe
distinguir "salvou" de "salvou o estado errado".

## What Changes

- **Metadados ao lado do savestate** (sidecar `.re.json`): `version`, `gamecode`, `frame`,
  `pc` (quando há debugger), `size`, `crc32`, `created_at`, `label` e `owner`. O formato binário
  do melonDS **não muda** (compatível com a UI).
- **Save verificado**: gravação atômica (temp + rename), com `crc32` calculado e relido; a
  resposta SHALL incluir os metadados e `verified=true` só após conferir tamanho+hash.
- **Load validado antes de aplicar**: confere existência do sidecar, `gamecode`, tamanho e
  `crc32` **antes** de tocar no estado; divergência → erro claro, sem carregar. Depois de
  carregar, faz **round-trip** (`frame` igual ao metadado; `pc` quando o gdb está anexado) e
  reporta `verified`/divergência.
- **Savestates nomeados e com dono**: `savestate.save/load` aceitam `name` (além de `slot`,
  com `path` mantido para uso direto) e `owner`/`label`; o canal resolve `name` para um
  namespace dedicado (`savestate_named_<name>.sav`) no diretório de savestates do emulador,
  fora da numeração da UI. Um `.lock` (flock) impede dois escritores no mesmo arquivo; `load`
  de outro `owner` exige `force=true`.
- **Listagem**: `savestate.list`/tool `savestate_list` mostra metadados, dono e se o arquivo
  foi alterado externamente (hash atual ≠ hash do sidecar).
- **Guard do debugger**: com o gdb anexado e o alvo haltado **fora de um limite de frame**, o
  save SHALL registrar `mid_frame=true` (aviso + dica), em vez de fingir consistência.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `control-channel`: savestate com sidecar verificado, `name`/`owner`/`label`, validação
  pré-load, round-trip pós-load e listagem de metadados.
- `mcp-control-tools`: tools de savestate com nome/dono, verificação e listagem; erros claros
  em vez de `ok` silencioso.

## Impact

- Emulador: `src/frontend/qt_sdl/ControlServer.{h,cpp}` (`savestate.*` com `path`/`owner`,
  sidecar, hash, flock); sem alterar o formato binário serializado nem o comportamento de
  emulação.
- MCP: `tools/control.py` (`savestate_save/load/list`), com hints acionáveis por motivo;
  testes com canal fake e com sidecar em diretório temporário.
- Compatibilidade: slots numéricos da UI continuam funcionando; o sidecar é opcional na
  leitura (ausente → aviso de "não verificado", não erro).
