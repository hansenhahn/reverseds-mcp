## 1. Emulador — controle de frame (frontend)

- [ ] 1.1 Primitivo interno de "esperar o próximo vblank + parar", na `EmuThread` (O(1), sem alocação). Verificar: compila e o laço de quadro para no vblank com framebuffer composto.
- [ ] 1.2 `emu.step_frame(N)` e `emu.pause_at_next_frame()` sobre o primitivo, respondendo quando a parada ocorre. Verificar: sem parada agendada, custo por quadro nulo; `step_frame(N)` avança N numa chamada.

## 2. MCP — tools

- [ ] 2.1 Tools finas `emu_step_frame` e `emu_pause_at_next_frame` (sem expor `run_until_vblank`). Verificar: agente lista as 2 tools.
- [ ] 2.2 Smoke com emulador: `step_frame(1)` num frame e captura reflete o frame; `step_frame(60)` avança ~1 s. Verificar: captura determinística entre chamadas.

## 3. Validação

- [ ] 3.1 Build do melonDS sem regressão; smoke existente do MCP verde. Verificar: build e `pytest`/`smoke-test.sh` OK.
- [ ] 3.2 `openspec validate add-frame-control --strict` OK. Verificar: comando sem erro.
