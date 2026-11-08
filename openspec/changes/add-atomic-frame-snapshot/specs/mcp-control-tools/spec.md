## ADDED Requirements

### Requirement: Tool de status e passo com captura

O MCP SHALL expor `emu_status()` (repassando `emu.status`) e `emu_step_frame(n, snapshot=False)`
(repassando `snapshot`). O docstring de `emu_step_frame` SHALL descrever o fluxo atômico
"avança `N` → captura no VBlank do quadro final → para" e recomendar `gpu3d_*` com
`source=last` logo depois. `emu_status` SHALL devolver `error` + `hint` (não exceção) quando o
canal não responder.

#### Scenario: Status pelo MCP
- **WHEN** o agente chama `emu_status` com o alvo parado
- **THEN** recebe `halted`, `frame` e o estado do snapshot em cache

#### Scenario: Captura no passo
- **WHEN** o agente chama `emu_step_frame(n, snapshot=true)`
- **THEN** o payload enviado ao canal inclui `snapshot=true` e o retorno traz `frame` e
  `snapshot_frame`

#### Scenario: Canal indisponível
- **WHEN** o canal de controle não responde
- **THEN** `emu_status` retorna `{"error", "hint"}` sem levantar exceção
