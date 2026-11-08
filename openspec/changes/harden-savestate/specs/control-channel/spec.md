## MODIFIED Requirements

### Requirement: Savestate

O sistema SHALL permitir `savestate.save` e `savestate.load` em um **slot**, **nome** ou
**caminho** (`path`) identificado, restaurando o estado completo da emulação (CPU, memória e
periféricos) sem alterar o formato binário nativo do melonDS. Um `name` SHALL ser sanitizado
(`[A-Za-z0-9._-]`, sem `..`, não puramente numérico) e resolvido para
`savestate_named_<name>.sav` no diretório de savestates do emulador, separado dos slots
numéricos da UI. Cada gravação SHALL produzir um sidecar
`.re.json` com `version`, `gamecode`, `frame`, `pc`, `size`, `crc32`, `created_at`, `label`,
`owner` e `mid_frame`, gravado de forma atômica. `savestate.load` SHALL validar **antes** de
aplicar (sidecar presente, `gamecode` do ROM carregado, tamanho e `crc32`) e SHALL recusar o
load com erro claro quando a validação falhar, sem tocar no estado. Após aplicar, SHALL fazer
round-trip de `frame` (e `pc` quando o debugger estiver anexado) e reportar `verified` e
divergências. `savestate.list` SHALL listar os estados com metadados, `owner` e `clobbered`
(quando o hash atual do binário divergir do sidecar). O sistema SHALL usar lock de arquivo
para impedir escrita concorrente e SHALL exigir `force=true` para carregar um estado de outro
`owner`.

#### Scenario: Salvar e restaurar
- **WHEN** o agente salva em um slot e depois carrega o mesmo slot
- **THEN** o estado da emulação volta ao ponto salvo e a resposta traz `verified=true`

#### Scenario: Save verificado
- **WHEN** o agente salva o estado
- **THEN** a resposta só indica sucesso após conferir tamanho e `crc32` do arquivo gravado

#### Scenario: Arquivo adulterado
- **WHEN** o binário não bate com o `crc32`/tamanho do sidecar
- **THEN** o `load` falha com erro claro e o estado atual permanece intacto

#### Scenario: Gamecode divergente
- **WHEN** o sidecar registra um `gamecode` diferente do ROM carregado
- **THEN** o `load` é recusado com erro acionável, sem carregar

#### Scenario: Round-trip após o load
- **WHEN** o load é aplicado com sucesso
- **THEN** o `frame` (e o `pc`, com gdb) conferem com o metadado e a resposta traz `verified`

#### Scenario: Estado de outro dono
- **WHEN** o agente tenta carregar um estado cujo `owner` não é o seu
- **THEN** o `load` é recusado, a menos que `force=true`

#### Scenario: Slot sobrescrito por fora
- **WHEN** outro processo sobrescreve o arquivo do slot
- **THEN** `savestate.list` marca o estado como `clobbered=true`

#### Scenario: Estado antigo sem sidecar
- **WHEN** o estado foi gravado por versão anterior, sem sidecar
- **THEN** o load é permitido com `verified=false` e aviso, preservando a compatibilidade

#### Scenario: Save no meio de um quadro
- **WHEN** o alvo está haltado por breakpoint fora de um limite de frame e o agente salva
- **THEN** a resposta traz `mid_frame=true` com dica, sem impedir o save
