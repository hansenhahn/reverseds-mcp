## MODIFIED Requirements

### Requirement: Interpretação das tabelas de overlay

O sistema SHALL interpretar as tabelas de overlay do header da ROM (`arm9_overlay` e
`arm7_overlay`), devolvendo por overlay: `id`, `ram_address`, `ram_size`, `bss_size`,
`sinit_start`, `sinit_end`, `file_id`, `flags` e `compressed_size`. O `flags` cru SHALL
ser preservado; o campo de tamanho comprimido SHALL ser exposto em `compressed_size`.

#### Scenario: Listar overlays
- **WHEN** o agente lista os overlays
- **THEN** recebe as entradas (id, endereço de RAM, tamanho, bss, sinit, file_id, flags e
  compressed_size) do ARM9 e do ARM7

#### Scenario: ROM sem overlays ARM7
- **WHEN** a ROM não possui overlays ARM7 (tabela vazia)
- **THEN** o sistema reporta lista vazia para o ARM7, sem erro

### Requirement: Overlay por endereço de RAM

O sistema SHALL resolver um endereço de RAM para **todos** os overlays candidatos que o
contêm, usando o intervalo `[ram_address, ram_address + ram_size)`. Cada candidato SHALL
incluir `offset_file` (`addr - ram_address`) e, quando a base de código for conhecida,
`offset_code` (`addr - code_base`). A resolução SHALL sinalizar `ambiguous=true` quando
houver mais de um candidato, em vez de escolher o primeiro silenciosamente.

#### Scenario: Endereço dentro de um overlay
- **WHEN** o endereço pertence a um único overlay
- **THEN** o sistema devolve um candidato, `ambiguous=false` e `offset_file` correto

#### Scenario: Endereço em overlays com base compartilhada
- **WHEN** dois ou mais overlays compartilham a mesma `ram_address` e cobrem o endereço
- **THEN** o sistema devolve todos os candidatos e `ambiguous=true`

#### Scenario: Base de código conhecida
- **WHEN** o chamador informa `code_base` dentro do intervalo do overlay
- **THEN** cada candidato inclui `offset_code` e a resolução inclui `prefix_size`

#### Scenario: Endereço fora de overlays
- **WHEN** o endereço de RAM não pertence a nenhum overlay
- **THEN** o sistema não devolve candidatos (sem erro)

## ADDED Requirements

### Requirement: Detalhes de overlay

O sistema SHALL expor `overlay_details` para um overlay (por `index` e `core`), combinando os
campos do y9 (`ram_address`, `ram_size`, `bss_size`, `sinit_start`, `sinit_end`, `file_id`,
`flags`), os dados do FAT (`file_offset`, `file_size`), a compressão (`compressed`,
`compressed_size`) e, opcionalmente, a base de código (`code_base`, `prefix_size`). A tool
SHALL ser read-only e SHALL retornar erro claro para um `index` inexistente ou um `code_base`
fora do intervalo do overlay.

#### Scenario: Detalhes de um overlay
- **WHEN** o agente pede os detalhes de um overlay existente
- **THEN** recebe os campos do y9, o `file_offset`/`file_size` do FAT e a compressão

#### Scenario: Overlay comprimido
- **WHEN** o `file_size` do FAT é menor que `ram_size`
- **THEN** o overlay é reportado como comprimido, com `compressed_size` e `file_offset`
  coerentes com o FAT

#### Scenario: Overlay não comprimido
- **WHEN** o `file_size` do FAT é igual a `ram_size` (ou o campo de compressão é zero)
- **THEN** o overlay é reportado como não comprimido, sem inventar `compressed_size`

#### Scenario: Base de código explícita
- **WHEN** o agente informa `code_base` dentro do intervalo do overlay
- **THEN** o resultado inclui `code_base` e `prefix_size` (`code_base - ram_address`)

#### Scenario: Sem base de código
- **WHEN** o agente não informa `code_base` e não há seleção ativa com base
- **THEN** `code_base` e `prefix_size` são `null`, sem inventar um prefixo

#### Scenario: Overlay inexistente
- **WHEN** o `index` não existe na tabela do core
- **THEN** a tool retorna `error` + `hint`, sem derrubar a sessão
