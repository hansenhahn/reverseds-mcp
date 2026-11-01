## 1. Modelo de símbolos

- [x] 1.1 Estender `Symbol` com `kind`, `comment` e `overlay` (defaults) e `SymbolTable` com
  `add`, `all`, `to_json`/`from_json`, `merge` e `RLock` (thread-safe), mantendo
  `from_map`/`resolve`. Verificar: testes de domínio para add/substituição, merge, JSON e
  resolução por vizinho.

## 2. Persistência e tools

- [x] 2.1 No `Bridge`, carregar `symbols.json` lazy na primeira leitura e gravar após
  `symbol_define`/`symbol_load` (tolerante a arquivo ausente/corrompido). Verificar: teste com
  `FileStore` fake; restart simulado recarrega.
- [x] 2.2 `symbol_define(addr, name, kind, comment, overlay)`, `symbol_list(kind=None)` e
  `symbol_load(path, merge=True)` (merge por padrão; `merge=False` substitui). Verificar:
  testes de tools com fake; descoberta no `list_tools`.

## 3. Anotação

- [x] 3.1 `disassemble` inclui `symbol` da instrução e `target_symbol` para o primeiro
  `0x...` do operando; `debug_backtrace` preenche `function` via símbolo quando o gdb der
  `null`. Verificar: testes com fake debugger/símbolos.
- [x] 3.2 `find_writer`/`find_reader`, `hit_log_read` e `addr_valid` incluem o símbolo
  resolvido. Verificar: testes de tools.

## 4. Snippets de decomp

- [x] 4.1 Criar `application/decomp.py` (serviço sobre `FileStore`) e
  `decomp_snippet(addr, c=None, asm=None)`; persistir em `decomp.json`. Verificar: teste de
  gravação/consulta/restart simulado.

## 5. Validação

- [x] 5.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-re-symbols --strict` verdes.
- [x] 5.2 Smoke real: definir um símbolo, desmontar um endereço conhecido e ver a anotação;
  registrar/consultar um snippet. (Sem emulador, usar o fake nos testes.)

> Validado em 2026-11-01: `pytest` (141), `pyright`, `lint-imports` e
> `openspec validate --strict` verdes. Persistência real coberta por um teste com duas
> instâncias de `Bridge`.
