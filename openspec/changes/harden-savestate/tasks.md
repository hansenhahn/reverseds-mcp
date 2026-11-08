## 0. Spike (viabilidade) — PRIMEIRO

- [ ] 0.1 Spike no fork: salvar um slot com o alvo haltado por `emu.step_frame`, gravar o
  sidecar (hash+frame), carregar o mesmo slot com o gdb anexado e comparar `frame` antes/depois
  e o PC. Verificar: o round-trip confirma `frame` (e `pc` com gdb); um save feito **com a UI**
  tem hash diferente do sidecar e é detectado. Se o savestate do melonDS não for consistente no
  ponto de parada, reavaliar (forçar limite de frame antes de salvar).

## 1. Emulador — sidecar e gravação verificada

- [x] 1.1 Gravar o estado em `.tmp`, calcular `crc32`/`size` e fazer `rename` atômico; gravar o
  sidecar `.re.json` (`version`, `gamecode`, `frame`, `pc`, `size`, `crc32`, `created_at`,
  `label`, `owner`, `mid_frame`). Verificar: após o save, binário e sidecar existem; o hash do
  binário bate com o sidecar.
- [x] 1.2 Retornar na resposta `verified=true` apenas após reler e conferir tamanho+hash;
  caso contrário `error` com o motivo. Verificar: corromper o `.tmp` de propósito faz o save
  falhar (teste unitário no `ControlServer`/helper).

## 2. Emulador — validação e round-trip no load

- [x] 2.1 No `savestate.load`, validar antes de aplicar: sidecar presente, `gamecode` igual ao
  ROM carregado, `size` e `crc32` iguais ao arquivo. Divergência → erro claro, **sem** carregar.
  Verificar: trocar o gamecode no sidecar bloqueia o load; arquivo corrompido bloqueia.
- [x] 2.2 Após carregar, comparar `frame` com o metadado e `pc` quando o gdb está anexado;
  retornar `verified`/`divergence` (sem `ok` silencioso). Verificar: load íntegro → `verified`;
  sidecar de outro frame → `verified=false` com divergência reportada.
- [x] 2.3 Savestate com o gdb anexado: detectar `mid_frame` e retornar o aviso + dica, sem
  impedir o save. Verificar: save num breakpoint de meio de quadro retorna `mid_frame=true`.

## 3. Emulador — nomes, dono e lock

- [x] 3.1 `savestate.save/load` aceitam `name` (sanitizado, não numérico, sem `..`) e
  `owner`/`label`; `name` resolve para `savestate_named_<name>.sav` no diretório do emulador.
  Verificar: nome válido salva; `../x` e nome numérico são rejeitados.
- [x] 3.2 `flock` no arquivo durante validação+load e durante o save; `load` de `owner`
  diferente exige `force=true`. Verificar: segundo escritor concorrente recebe erro; `force`
  libera o load.
- [x] 3.3 Adicionar `savestate.list` com metadados de cada slot/nome, dono, e `clobbered` quando
  o hash atual ≠ sidecar. Verificar: sobrescrever o binário por fora marca `clobbered=true`.

## 4. MCP

- [x] 4.1 `savestate_save(slot=0, name=None, label=None, owner=None)` e
  `savestate_load(slot=0, name=None, owner=None, force=False)`; o `name` é repassado ao canal
  (sem path local). Verificar: testes com canal fake confirmam `name`/`owner`/`force` no
  payload.
- [x] 4.2 Nova tool `savestate_list()` repassando `savestate.list`. Verificar: teste com canal
  fake devolve a lista e propaga erro.
- [x] 4.3 Erros do canal viram `error` + `hint` acionável (gamecode, hash, dono, mid-frame),
  nunca sucesso silencioso. Verificar: teste para cada motivo.

## 5. Documentação

- [x] 5.1 Atualizar README/skill com o fluxo "load antes de conectar o gdb" e o significado de
  `verified`/`clobbered`/`owner`. Verificar: inventário cita `savestate_list` e os campos.

## 6. Validação

- [ ] 6.1 Build do fork sem regressão; formato binário do savestate continua abrindo na UI.
  Verificar: salvar pelo MCP e carregar pela UI (e vice-versa).
- [x] 6.2 MCP: `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` verdes.
- [x] 6.3 `openspec validate harden-savestate --strict` verde.
- [ ] 6.4 Smoke real no KH: `savestate_save` no letreiro → `savestate_load` com o gdb
  anexado → `emu.status` com o mesmo `frame` e tela igual à capturada no save; adulterar o
  sidecar força erro claro. Verificar: round-trip confirma e não carrega estado divergente.
