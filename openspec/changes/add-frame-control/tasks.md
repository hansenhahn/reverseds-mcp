## 1. Emulador — step_frame (frontend)

- [x] 1.1 `EmuThread::emuStepFrames(n)`: contador no frame-step existente + bloqueio até zerar (condição). Verificar: chamada bloqueia até os N quadros rodarem e termina pausado.
- [x] 1.2 Laço: rodar um quadro por iteração enquanto `frameStepCount > 0`, parar no vblank com framebuffer composto, O(1) sem alocação. Verificar: sem avanço em andamento, custo por quadro nulo.
- [x] 1.3 Método `emu.step_frame` no canal de controle (param `n ≥ 1`). Verificar: `control-client.py` retorna após N quadros.

## 2. MCP — tool

- [x] 2.1 Tool fina `emu_step_frame(n)` (sem expor `run_until_vblank`/`pause_at_next_frame`). Verificar: agente lista a tool.
- [x] 2.2 Smoke com emulador: `emu_step_frame(1)` num frame e captura reflete o frame; `emu_step_frame(60)` avança ~1 s. Verificar: captura determinística entre chamadas.

## 3. Validação

- [x] 3.1 Build do melonDS sem regressão; smoke existente do MCP verde. Verificar: build e `pytest`/`smoke-test.sh` OK.
- [x] 3.2 `openspec validate add-frame-control --strict` OK. Verificar: comando sem erro.
