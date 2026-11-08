## ADDED Requirements

### Requirement: Status de execução e frame counter

O canal SHALL expor `emu.status`, atendido na thread de emulação, informando se a emulação
está `running`/`halted`, o **frame counter** atual e, quando houver, o `frame` do snapshot 3D
em cache com `age_frames` e `stale`. O método SHALL responder **com o alvo haltado** e o
`frame` SHALL permanecer estável entre chamadas enquanto o alvo estiver parado.

#### Scenario: Status com o alvo parado
- **WHEN** o gdb mantém o alvo parado e o agente chama `emu.status`
- **THEN** recebe `halted=true` e o `frame` atual, sem expirar

#### Scenario: Idade do snapshot
- **WHEN** existe um snapshot em cache de um quadro anterior e o alvo está rodando
- **THEN** `emu.status` informa `snapshot.frame`, `age_frames > 0` e `stale=true`

#### Scenario: Sem snapshot
- **WHEN** nenhum snapshot 3D foi capturado ainda
- **THEN** o campo de snapshot vem `null`, sem erro

### Requirement: Captura atômica no avanço de quadros

O canal SHALL aceitar `emu.step_frame` com `snapshot` (bool). Com `snapshot=true`, a captura
3D SHALL ser armada antes de rodar e consumida no **VBlank do último** quadro avançado, na
mesma operação que termina com o alvo parado. A resposta SHALL incluir o `frame` final e o
`frame` capturado; o snapshot SHALL descrever esse quadro completo.

#### Scenario: Step com captura
- **WHEN** o agente chama `emu.step_frame(n, snapshot=true)`
- **THEN** a emulação avança `n` quadros, o snapshot é copiado no VBlank do quadro final e o
  alvo termina parado, com `frame` e `snapshot_frame` iguais

#### Scenario: Step sem captura
- **WHEN** o agente chama `emu.step_frame(n)` sem `snapshot`
- **THEN** o comportamento atual é mantido e o cache de snapshot não é alterado

### Requirement: Seleção de snapshot 3D

As leituras `3d.state`, `3d.polygons`, `3d.textures` e `3d.texture` SHALL aceitar `source` com
os valores `auto` (padrão), `last` e `fresh`. Com `last`, SHALL servir o snapshot em cache
(mesmo `frame`) sem exigir VBlank, inclusive com o alvo parado, e SHALL informar `frame`,
`age_frames` e `stale`; sem cache e com o alvo parado, SHALL retornar erro com dica
acionável. Com `fresh`, SHALL exigir a emulação rodando e retornar erro claro (não timeout)
quando parada. Com `auto`, SHALL capturar apenas se não houver cache.

#### Scenario: Leitura consistente com o alvo parado
- **WHEN** o alvo está parado após `emu.step_frame(n, snapshot=true)` e o agente lê
  `3d.state` e `3d.polygons` com `source=last`
- **THEN** as duas respostas trazem o mesmo `frame` e `age_frames=0`, sem expirar

#### Scenario: Fresh com o alvo parado
- **WHEN** o agente pede `source=fresh` com a CPU haltada
- **THEN** recebe erro claro com dica para usar `emu.step_frame(1, snapshot=true)`

#### Scenario: Sem cache e parado
- **WHEN** não há snapshot em cache e o alvo está parado
- **THEN** a leitura retorna erro + dica, em vez de timeout genérico
