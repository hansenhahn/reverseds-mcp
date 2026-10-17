# nds-overlays Specification

## Purpose

Interpreta as tabelas de overlay do cartucho (`y9`/`y7`), expondo os overlays e resolvendo
endereços de RAM para o overlay correspondente.

## Requirements

### Requirement: Interpretação das tabelas de overlay

O sistema SHALL interpretar as tabelas de overlay do header da ROM (`arm9_overlay` e
`arm7_overlay`), devolvendo por overlay: `id`, `ram_address`, `ram_size`, `bss_size` e
`file_id`.

#### Scenario: Listar overlays
- **WHEN** o agente lista os overlays
- **THEN** recebe as entradas (id, endereço de RAM, tamanho, bss, file_id) do ARM9 e do ARM7

#### Scenario: ROM sem overlays ARM7
- **WHEN** a ROM não possui overlays ARM7 (tabela vazia)
- **THEN** o sistema reporta lista vazia para o ARM7, sem erro

### Requirement: Overlay por endereço de RAM

O sistema SHALL resolver um endereço de RAM para o overlay que o contém, usando o intervalo
`[ram_address, ram_address + ram_size)`.

#### Scenario: Endereço dentro de um overlay
- **WHEN** o agente informa um endereço de RAM ocupado por um overlay
- **THEN** o sistema devolve o overlay e o deslocamento dentro dele

#### Scenario: Endereço fora de overlays
- **WHEN** o endereço de RAM não pertence a nenhum overlay
- **THEN** o sistema não devolve overlay (sem erro)
