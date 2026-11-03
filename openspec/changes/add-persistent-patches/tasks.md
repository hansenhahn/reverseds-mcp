## 1. Modelo e serviço

- [x] 1.1 Adicionar serialização `Patch.to_specs`/`from_json` (ou equivalente) no domínio.
  Verificar: round-trip de um patch válido e rejeição de JSON inválido.
- [x] 1.2 Criar `application/patch_state.py` (`PatchManager`) com `set`, `apply`, `clear`,
  `list` e carga de `patches.json`; escrita via `Debugger.write_memory`.
  Verificar: fake debugger/store — aplica, persiste, recarrega e reaplica.

## 2. Integração

- [x] 2.1 `Bridge.patch_manager()` lazy + reset no `close`.
- [x] 2.2 `savestate_load` chama `PatchManager.apply()` após o load; falha de gdb não
  derruba o load (`patch_error` + hint).
- [x] 2.3 Tools `patch_set`, `patch_apply`, `patch_clear`, `patch_list`.

## 3. UI de ferramenta

- [x] 3.1 `patch_set(patches, persist=True, apply=True)` valida via `Patch`, aplica e
  persiste; retorna writes/bytes/regions/path.
- [x] 3.2 `patch_apply()`/`patch_clear()`/`patch_list()` com mensagens claras quando não há
  conjunto ativo ou gdb.
- [x] 3.3 Docstrings e skill citam que overlay reload exige `patch_apply` (D3 é follow-up).

## 4. Validação

- [x] 4.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-persistent-patches --strict`.
- [x] 4.2 Smoke real: `patch_set` em uma instrução do menu, `savestate_load`, conferir com
  `mem_read` que os bytes voltaram; `patch_clear`; testar `apply=false`.

### Smoke real (2026-11-02)

- `patch_set` em `0x023FF000` (`deadbeef`) aplicou e persistiu `patches.json`.
- `savestate_load` sem gdb retornou `patch_error` + hint (load OK).
- Após reconectar, `patch_apply` reescreveu os bytes; `patch_list` mostrou o conjunto.
- `patch_clear` limpou o conjunto; os bytes originais foram restaurados manualmente.
