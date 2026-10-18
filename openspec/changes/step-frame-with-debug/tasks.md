## 0. Spike (viabilidade) — PRIMEIRO

- [ ] 0.1 Spike mínimo no fork: com o **debugger conectado**, fazer `emu.step_frame(N)` avançar **exatamente N** quadros e **cessar parado**, e a leitura seguinte (captura/vídeo) refletir o **mesmo** quadro. Verificar: `debug_connect` → `emu_step_frame(10)` → captura antes/depois de um `video_state` **idênticas** (não andou). *(Valida o mecanismo antes de implementar de verdade; se não vingar, reavaliar o design.)*

## 1. Emulador — parada unificada

- [ ] 1.1 O stub **cede** durante o `step_frame` (a CPU roda N quadros) e **volta a segurar** no fim (o mesmo "parado"). Verificar: com gdb conectado, `step_frame(N)` avança N.
- [ ] 1.2 Servir o stub **com o emulador parado** (para `debug_connect`/leitura não travarem). Verificar: parado por `step_frame`, `debug_connect` responde.
- [ ] 1.3 `continue`/`debug_resume` **desfaz** a parada. Verificar: após `debug_resume`, a emulação avança.
- [ ] 1.4 Remover `emu.pause`/`emu.resume` do `ControlServer` (os `emuPause/emuUnpause` internos do `render_layer` permanecem). Verificar: os métodos somem.

## 2. MCP

- [ ] 2.1 Remover as tools `emu_pause`/`emu_resume`; remover o nudge do `debug_connect` (usava `emu.resume`); ajustar docstrings (`emu_step_frame`, `render_layer`).
- [ ] 2.2 Smoke: `step_frame(10)` (gdb conectado) → captura → **mesmo quadro**; `debug_resume` → avança.

## 3. Validação

- [ ] 3.1 Build do melonDS sem regressão; `pytest`/`pyright`/`lint-imports` verdes.
- [ ] 3.2 `openspec validate step-frame-with-debug --strict` OK.
