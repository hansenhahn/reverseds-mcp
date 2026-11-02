# add-overlay-aware-resolution

Frente A do roadmap (A1 + A2): resolver overlays com base compartilhada sem “primeiro
match” e expor os detalhes que separam offset de arquivo, offset de código e compressão.

- **A1** — `overlay_for_address` devolve todos os candidatos + `ambiguous`; seleção ativa
  (`overlay_select`) para o agente declarar a overlay residente; `rom_details.runtime` e
  `addr_valid` param de escolher silenciosamente.
- **A2** — `overlay_details` combina y9 (`sinit_start/end`, `flags`), FAT (`file_offset`,
  `file_size`), compressão (`compressed`, `compressed_size`) e `code_base`/`prefix_size`
  opcionais.

Sem mudança no emulador. A3 (símbolos por overlay) fica para um change separado.
