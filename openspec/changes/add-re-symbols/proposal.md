## Why

Hoje os nomes descobertos na sessão (`desenha_painel`, `prepara_texto`, campos de struct) vivem
na documentação e no contexto do agente. As ferramentas continuam mostrando endereços crus, e
cada sessão redescobre os mesmos nomes. O decomp em C e os recortes ASM também ficam em
documentos externos, sem vínculo consultável com o endereço.

## What Changes

- **Símbolos/aliases persistentes**: `symbol_define(addr, name, kind, comment, overlay)` e
  `symbol_list`; `symbol_load` passa a **mesclar** um `.map` com os aliases existentes. A tabela
  é gravada em `RE_MCP_OUT_DIR/symbols.json` e recarregada no restart.
- **Anotação automática**: `disassemble` inclui o símbolo da instrução e o símbolo do alvo de
  branch/call; `debug_backtrace`, `find_writer`/`find_reader`, `hit_log_read` e `addr_valid`
  incluem o nome do símbolo quando houver.
- **Decomp snippets**: `decomp_snippet(addr, c, asm)` registra/consulta um trecho C+ASM por
  endereço, persistido em `RE_MCP_OUT_DIR/decomp.json`.
- **Sem Ghidra por enquanto**: o modelo é interno; export/import para Ghidra fica para depois.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-re-workflows`: alias/símbolos persistentes, merge de `.map`, anotação de hits e
  `addr_valid`, e snippets de decomp.
- `mcp-debug-tools`: `disassemble` anotado e `debug_backtrace` com símbolo.

## Impact

- MCP: `domain/symbols.py` (modelo + JSON + thread-safety), `application/decomp.py` (novo),
  `bridge.py` (persistência/lazy load), `tools/re.py`, `tools/debug.py`, testes.
- Emulador: **nenhuma mudança**.
- Sem custo por frame; leitura/escrita só sob demanda.
