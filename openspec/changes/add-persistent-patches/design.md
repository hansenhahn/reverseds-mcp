## Context

Ver `proposal.md`. `domain/patch.py` já tem `Patch`/`PatchWrite` com validação (≤256
escritas, ≤64 KiB, hex, endereço). `PatchComparer` lê memória e compara ASM×C. Falta
**manter** um patch aplicado ao longo de reloads e entre reinícios do MCP.

## Goals / Non-Goals

**Goals:**
- Um conjunto ativo de escritas, aplicado e persistido em `patches.json`.
- Reaplicar automaticamente após `savestate_load`.
- Aplicar/limpar/listar manualmente; `patch_apply()` para reload de overlay.
- Persistir entre restarts do MCP.
- Reutilizar a validação do `Patch`.

**Non-Goals:**
- Detectar reload de overlay automaticamente (depende do hook D3).
- Reverter para os bytes originais (`patch_clear` só limpa a lista).
- Múltiplos conjuntos nomeados (MVP: um conjunto ativo).
- Patches de ROM/arquivo; isto é RAM em runtime.

## Decisions

### 1. `PatchManager` (application)

`PatchManager(debugger, files)`:

- `set(specs, persist=True, apply=True) -> Patch`: valida com `Patch.from_specs`; se
  `apply`, escreve via `Debugger.write_memory`; guarda o patch; se `persist`, grava JSON.
- `apply() -> int`: reescreve o conjunto ativo; retorna número de writes.
- `clear(persist=True)`: esquece o conjunto (não restaura bytes); grava vazio.
- `list() -> Patch | None`.
- Carrega `patches.json` no primeiro uso; JSON inválido → log + conjunto vazio.

Formato:

```json
{"writes": [{"addr": 33554432, "bytes": "deadbeef"}], "active": true}
```

### 2. Um conjunto ativo

`patch_set` substitui o conjunto anterior (não acumula). Para experimentos alternativos, o
agente salva/restaura dumps ou usa `session` (D2) no futuro.

### 3. Reaplicação

- `savestate_load`: após o load, chama `PatchManager.apply()`; se o gdb não estiver
  conectado/parado, o load continua e o resultado traz `patch_error` + hint.
- `emu_reset`: **não** reaplica automaticamente (o overlay ainda não foi carregado; o patch
  seria sobrescrito). Usar `patch_apply()` depois do boot.
- Overlay reload: `patch_apply()` explícito até D3 (`overlay_loaded`).

### 4. Persistência e `apply`

- `persist=true` grava `patches.json`; `false` mantém só na sessão.
- `apply=false` permite definir o conjunto sem gdb; aplicar depois com `patch_apply()`.
- `patch_clear` não reverte bytes (evita “desfazer” estado que mudou desde a aplicação).

### 5. Falhas

- Escrita inválida → `error` + hint, sem alterar o conjunto atual.
- Falha de gdb ao aplicar → `error` + hint; o conjunto persistido permanece.
- `savestate_load` com patch ativo e sem gdb → load OK + `patch_error`.

## Risks / Trade-offs

- [Patch aplicado antes do overlay carregar] → pode ser sobrescrito; reaplicar por
  `patch_apply()` depois do load.
- [Estado mudou desde o patch] → reaplicar sobrescreve; é o comportamento desejado para
  experimentos, mas não é “revert seguro”.
- [Patch grande] → limites do `Patch` (256 writes/64 KiB).
- [Persistência entre ROMs] → `patches.json` é do out dir; o agente deve limpar/trocar de
  out dir se mudar de jogo.

## Migration Plan

Aditivo. Atualizar `mcp-re-workflows` e testes. `pytest`, `pyright`, `lint-imports`,
`openspec validate --strict`; smoke: patch no menu, `savestate_load`, conferir bytes
reaplicados.

## Open Questions

- `patch_revert` com bytes originais? (Follow-up.)
- Múltiplos conjuntos nomeados? (Só se necessário.)
- Persistir no `session_save/load` (D2) em vez de arquivo próprio? (D2 pode absorver.)
