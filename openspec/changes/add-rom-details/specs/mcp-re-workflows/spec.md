## ADDED Requirements

### Requirement: Detalhes completos da ROM

O MCP SHALL oferecer `rom_details` para a ROM carregada no emulador, retornando a identidade,
o header completo (GBATEK), a contagem de arquivos NitroFS, a contagem de overlays ARM9/ARM7
e, quando o debugger estiver conectado, o `core`, o `pc` e o overlay atual. Sem ROM carregada,
SHALL retornar `loaded=false`; a tool SHALL ser read-only.

#### Scenario: ROM carregada
- **WHEN** o agente chama `rom_details` com uma ROM carregada
- **THEN** recebe identidade, header completo, contagens de arquivos/overlays e `runtime`

#### Scenario: Debugger conectado
- **WHEN** o gdb está conectado e a CPU está parada
- **THEN** `runtime` inclui `core`, `pc` e o overlay atual (ou `null` se o PC não estiver em
  um overlay)

#### Scenario: Sem debugger
- **WHEN** o gdb não está conectado
- **THEN** `runtime` é `null` e o restante dos detalhes continua disponível

#### Scenario: Sem ROM
- **WHEN** não há ROM carregada
- **THEN** a tool retorna `loaded=false`, sem erro de execução
