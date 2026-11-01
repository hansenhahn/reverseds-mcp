## Context

Ver `proposal.md` — Why. A ROM já é a fonte da verdade (`rom.info`/`rom.read`) e o domínio
`NdsHeader` lê apenas os primeiros 0x60 bytes (FNT/FAT/overlays). O `rom_info` devolve
identidade; `overlay_for_address` resolve o overlay, mas o agente precisa cruzar PC/overlay.

## Goals / Non-Goals

**Goals:**
- Uma chamada com identidade, header completo, derivados e runtime overlay.
- Sem mudança no emulador; leitura sob demanda.
- Tolerant a header parcial/sintético (campos ausentes = 0).

**Non-Goals:**
- Recalcular/validar CRC do header/logo (mostramos os valores armazenados).
- Detectar automaticamente “build do savestate ≠ ROM”.
- Export/import Ghidra.
- Resolver overlays que compartilham a mesma base (o runtime usa o primeiro match da tabela).

## Decisions

- **Ler 0x200 via `rom.read`.** `NdsHeader.from_bytes` aceita ≥0x60 e preenche o resto com
  zero; assim fixtures antigas seguem válidas.
- **`CartFs.header()` na porta.** O adaptador `ChannelRom` lê o header; a tool compõe
  `RomDetails`-style com `file_count`/`overlay_list`. Alternativa: tool acessar o adaptador
  concreto — quebraria a porta.
- **Runtime opcional.** Se `debugger.core()` for None, `runtime=null`; se conectado, lê PC e
  resolve overlay via `OverlayTable.for_address`. `DebugError` → `runtime=null` (não derruba
  a tool).
- **Sem emulador.** O canal já serve a ROM; nenhuma alteração no fork.
- **Sem recomputar CRC.** Os valores armazenados no header são reportados; validação pode ser
  um follow-up.

## Risks / Trade-offs

- [Header sintético/truncado] → pad com zero; campos podem ser 0, sem falha.
- [Overlay 22 × 25 na mesma base] → runtime mostra o primeiro match; o campo `overlay` do
  símbolo/`addr_valid` continua disponível para o agente.
- [GDB rodando/erro ao ler PC] → runtime null; `rom_details` continua útil.
- [ROM trocada no meio] → `rom_info`/`rom.read` usam a identidade atual; a próxima chamada
  corrige.

## Migration Plan

Aditivo; nova tool + método de porta. Validar com `pytest`, `pyright`, `lint-imports` e
`openspec validate --strict`; smoke real com uma ROM carregada.

## Open Questions

- Validar CRC do header contra o conteúdo? (Follow-up.)
- Reportar `overlay_details(id)` com compressão BLZ/LZ? (Follow-up.)
