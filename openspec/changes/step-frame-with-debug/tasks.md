## 0. Spike (viabilidade) — PRIMEIRO

- [x] 0.1 Spike mínimo no fork: com o **debugger conectado**, fazer `emu.step_frame(N)` avançar **exatamente N** quadros e **cessar parado**, e a leitura seguinte (captura/vídeo) refletir o **mesmo** quadro. Verificar: `debug_connect` → `emu_step_frame(10)` → captura antes/depois de um `video_state` **idênticas** (não andou). *(Valida o mecanismo antes de implementar de verdade; se não vingar, reavaliar o design.)*

## 1. Emulador — parada unificada

- [x] 1.1 O stub **cede** durante o `step_frame` (a CPU roda N quadros) e **volta a segurar** no fim (o mesmo "parado"). Verificar: com gdb conectado, `step_frame(N)` avança N.
- [x] 1.2 Servir o stub **com o emulador parado** (para `debug_connect`/leitura não travarem). Verificar: parado por `step_frame`, `debug_connect` responde.
- [x] 1.3 `continue`/`debug_resume` **desfaz** a parada. Verificar: após `debug_resume`, a emulação avança.
- [x] 1.4 Remover `emu.pause`/`emu.resume` do `ControlServer` (os `emuPause/emuUnpause` internos do `render_layer` permanecem). Verificar: os métodos somem.

## 2. MCP

- [x] 2.1 Remover as tools `emu_pause`/`emu_resume`; remover o nudge do `debug_connect` (usava `emu.resume`); ajustar docstrings (`emu_step_frame`, `render_layer`).
- [x] 2.2 Smoke: `step_frame(10)` (gdb conectado) → captura → **mesmo quadro**; `debug_resume` → avança.

## 3. Validação

- [x] 3.1 Build do melonDS sem regressão; `pytest`/`pyright`/`lint-imports` verdes.
- [x] 3.2 `openspec validate step-frame-with-debug --strict` OK.

> Implementado no fork do melonDS em dois PRs na branch de integração `dev/gdb-watchpoints`:
> a parada unificada (0.1, 1.1–1.3) veio no PR #10 (`feat/step-frame-with-debug`) e a
> remoção de `emu.pause`/`emu.resume` do `ControlServer` (1.4) na branch
> `feat/remove-emu-pause-resume`. No MCP, removidas as tools `emu_pause`/`emu_resume` e
> ajustadas as docstrings (`emu_step_frame`, `render_layer`) e o README. O *nudge* do
> `debug_connect` já não existia no código.
>
> Verificado nesta sessão (emulador real, Hotel Dusk): `debug_connect` → capturas repetidas
> **idênticas** (parado, não anda); `emu_step_frame(10)` → captura **diferente** e depois
> **idêntica** (avançou e parou no quadro); `debug_resume` → captura **diferente** (voltou a
> andar). `emu.pause`/`emu.resume` agora respondem `method not found`; `emu.step_frame`
> continua OK. `pytest` (46), `pyright` (0 erros) e `lint-imports` (3 contratos) verdes.
