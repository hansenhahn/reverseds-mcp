## MODIFIED Requirements

### Requirement: Interpretação das tabelas de overlay

O sistema SHALL interpretar as tabelas de overlay do header da **ROM carregada no emulador**
(via canal de controle), devolvendo por overlay: `id`, `ram_address`, `ram_size`, `bss_size`
e `file_id`. Quando a ROM carregada mudar, as tabelas SHALL ser relidas da nova ROM.

#### Scenario: Listar overlays
- **WHEN** o agente lista os overlays
- **THEN** recebe as entradas (id, endereço de RAM, tamanho, bss, file_id) do ARM9 e do ARM7
  da ROM em execução

#### Scenario: ROM sem overlays ARM7
- **WHEN** a ROM não possui overlays ARM7 (tabela vazia)
- **THEN** o sistema reporta lista vazia para o ARM7, sem erro

#### Scenario: Troca de ROM
- **WHEN** outra ROM é carregada no emulador entre duas consultas
- **THEN** a consulta seguinte resolve os overlays da nova ROM
