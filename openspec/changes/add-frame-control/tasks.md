## 1. Emulador — controle de frame (frontend)

- [ ] 1.1 Mensagem/flag de parada na `EmuThread` (`step_frame`/`run_until_vblank`/`pause_at_next_frame`). Verificar: compila e o laço de quadro para no vblank.
- [ ] 1.2 Contador de quadros + parada no vblank com framebuffer composto, O(1) e sem alocação por quadro. Verificar: sem parada agendada, custo por quadro nulo (inspeção/profiling leve).
- [ ] 1.3 Métodos no canal de controle (`emu.step_frame`, `emu.run_until_vblank`, `emu.pause_at_next_frame`) respondendo quando a parada ocorre. Verificar: chamada via `control-client.py` retorna após a parada.

## 2. MCP — tools

- [ ] 2.1 Tools finas `emu_step_frame`/`emu_run_until_vblank`/`emu_pause_at_next_frame`. Verificar: agente lista as tools.
- [ ] 2.2 Smoke com emulador: `step_frame(1)` para num frame e `screen_capture` reflete o frame. Verificar: captura estável entre chamadas (determinística).

## 3. Validação

- [ ] 3.1 Build do melonDS sem regressão; smoke existente do MCP verde. Verificar: build e `pytest`/`smoke-test.sh` OK.
- [ ] 3.2 `openspec validate add-frame-control --strict` OK. Verificar: comando sem erro.
