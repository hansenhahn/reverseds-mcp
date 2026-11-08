## MODIFIED Requirements

### Requirement: Tools de savestate e execução

O MCP SHALL expor `savestate_save(slot|name, label, owner)`, `savestate_load(slot|name, owner,
force)` e `savestate_list()`. `name` SHALL ser repassado ao canal, que o resolve para um
namespace dedicado no diretório de savestates do emulador, fora da numeração da UI. As respostas SHALL
propagar `verified`, `clobbered`, `mid_frame` e `owner` do canal, e qualquer falha de
validação SHALL virar `error` + `hint` acionável, nunca sucesso silencioso.

#### Scenario: Salvar e restaurar
- **WHEN** o agente salva e depois carrega um slot
- **THEN** o estado volta ao ponto salvo e a resposta traz `verified=true`

#### Scenario: Savestate nomeado
- **WHEN** o agente salva com `name` e depois carrega pelo mesmo nome
- **THEN** o arquivo fica no namespace nomeado do emulador e não colide com slots da UI

#### Scenario: Carregar estado de outro dono
- **WHEN** o agente tenta carregar um estado de outro `owner` sem `force`
- **THEN** recebe `error` + `hint` e o estado não é carregado

#### Scenario: Listar estados
- **WHEN** o agente chama `savestate_list`
- **THEN** recebe os estados com metadados, dono e `clobbered`

#### Scenario: Falha de verificação
- **WHEN** o canal reporta hash/gamecode divergente ou arquivo adulterado
- **THEN** a tool devolve `error` + `hint`, sem relatar sucesso
