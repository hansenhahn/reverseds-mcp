## Why

Overlays diferentes podem compartilhar a mesma `ram_address`. Hoje
`overlay_for_address` devolve só o **primeiro** match, então `rom_details.runtime` e
`addr_valid` podem reportar a overlay 22 quando a residente é a 25 (ou vice-versa). Isso
contamina o decomp: a função é atribuída à unidade errada e o agente escreve no arquivo
errado.

Além disso, o `offset` devolvido é **file-relative** (`addr - ram_address`), enquanto a doc
de decomp pensa em **code-relative** (após um prefixo/sinit da overlay). Faltam também
`file_offset`/`file_size`, informação de compressão e os campos `sinit_start/end` da tabela
y9. Sem esses dados, o agente confunde offset de arquivo com offset de código e não sabe se
a overlay está comprimida.

## What Changes

- **A1 — resolução com candidatos.** `overlay_for_address` passa a devolver **todos** os
  overlays que cobrem o endereço (`overlays`), com `ambiguous=true` quando há mais de um. O
  campo `overlay`/`offset` continua existindo para compatibilidade, mas nunca escolhe um
  candidato silenciosamente quando há ambiguidade: usa a seleção ativa ou devolve `null`.
  `rom_details.runtime` e `addr_valid` seguem a mesma regra.
- **A1 — seleção ativa.** `overlay_select(index, core, code_base=None)` define a overlay
  considerada residente para as próximas consultas; `overlay_select(None)` limpa. É estado de
  sessão do MCP (não persiste, não muda o emulador) e representa uma **afirmação do agente**,
  não uma detecção automática.
- **A2 — `overlay_details`.** Nova tool read-only que retorna os campos do y9 (`ram_address`,
  `ram_size`, `bss_size`, `sinit_start`, `sinit_end`, `file_id`, `flags`), os dados do FAT
  (`file_offset`, `file_size`), a compressão (`compressed`, `compressed_size`) e,
  opcionalmente, a **base de código** (`code_base`/`prefix_size`) fornecida pelo chamador.
- **A2 — offsets explícitos.** Candidatos e `addr_valid` passam a devolver `offset_file`
  (sempre) e `offset_code` (quando a base de código é conhecida). A base de código é
  específica do jogo; o MCP não a infere.
- **Sem mudança no emulador.** Tudo usa `rom.info`/`rom.read` e o estado já disponível.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities

- `nds-overlays`: interpretação do y9 com sinit/flags/compressão; resolução por endereço
  devolvendo todos os candidatos e os dois offsets; detalhes por overlay.
- `mcp-re-workflows`: `overlay_for_address` com candidatos, `overlay_details`,
  `overlay_select`; `rom_details.runtime` e `addr_valid` sem primeiro-match silencioso.

## Impact

- MCP: `domain/overlays.py`, `application/ports/overlays.py`, `infra/ndsrom.py`,
  `application/overlays.py` (novo resolver/seleção), `bridge.py`, `tools/cart.py`,
  `tools/re.py`, testes.
- Emulador: **nenhuma mudança**.
- Docs/skill: rotular `file_offset` × `code_offset` e documentar a seleção ativa; sem
  endereços fixos de jogo.
