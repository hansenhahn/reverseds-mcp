## ADDED Requirements

### Requirement: Patches persistentes de RAM

O MCP SHALL manter um conjunto ativo de escritas `{addr, bytes}` (validado pelo modelo
`Patch`) e SHALL oferecer `patch_set(patches, persist=True, apply=True)`, `patch_apply()`,
`patch_clear()` e `patch_list()`. `patch_set` SHALL substituir o conjunto anterior, aplicar
na RAM quando `apply=true` e persistir em `patches.json` quando `persist=true`. Após
`savestate_load`, o MCP SHALL reaplicar o conjunto ativo automaticamente; uma falha do gdb
nessa reaplicação SHALL NOT falhar o load (o resultado SHALL trazer `patch_error`/hint).
Reload de overlay SHALL exigir `patch_apply()` explícito até existir o hook D3 (o MCP não
detecta o reload sozinho).

#### Scenario: Definir e aplicar
- **WHEN** o agente chama `patch_set` com escritas válidas e `apply=true`
- **THEN** os bytes são escritos na RAM e o conjunto fica listado por `patch_list`

#### Scenario: Sobreviver ao `savestate_load`
- **WHEN** há um conjunto ativo e o agente carrega um savestate
- **THEN** o MCP reaplica as escritas após o load

#### Scenario: Persistir entre restarts
- **WHEN** o agente define um patch com `persist=true` e o MCP reinicia
- **THEN** `patch_list`/`patch_apply` continuam vendo o conjunto salvo

#### Scenario: Definir sem gdb
- **WHEN** o agente usa `apply=false` sem o gdb conectado
- **THEN** o conjunto é gravado e pode ser aplicado depois com `patch_apply()`

#### Scenario: Overlay recarregou
- **WHEN** a overlay recarrega e o agente chama `patch_apply()`
- **THEN** as escritas são reaplicadas após o reload

#### Scenario: Limpar
- **WHEN** o agente chama `patch_clear()`
- **THEN** o conjunto ativo fica vazio (sem reverter bytes já escritos)

#### Scenario: Escrita inválida
- **WHEN** um `addr`/`bytes` é inválido ou o patch excede os limites
- **THEN** a tool retorna `error` + `hint` e não altera o conjunto atual

#### Scenario: Falha de gdb no load
- **WHEN** há patch ativo e `savestate_load` ocorre sem gdb
- **THEN** o load conclui e o resultado informa `patch_error` com hint
