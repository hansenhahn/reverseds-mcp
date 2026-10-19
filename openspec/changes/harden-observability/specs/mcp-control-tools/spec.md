## ADDED Requirements

### Requirement: Captura vazia é erro explícito

Quando `screen_capture` decodifica **0 frames**, o MCP SHALL retornar `error` acompanhado de
`hint` explicando que a captura veio vazia (nenhum frame decodificado). O MCP NÃO SHALL
retornar `{"paths": []}` silenciosamente como se a captura tivesse dado certo.

#### Scenario: Captura sem frames
- **WHEN** a captura não decodifica nenhum frame (payload vazio/incompleto)
- **THEN** a resposta traz `error` e `hint`, e nenhum caminho de PNG é retornado como sucesso
