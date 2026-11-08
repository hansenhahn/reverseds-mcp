## 0. Spike (viabilidade) — PRIMEIRO

- [ ] 0.1 Spike no fork: com o gdb conectado e o alvo parado, armar uma captura, rodar
  `emu.step_frame(1)` e confirmar que o snapshot do **VBlank do quadro alvo** é copiado antes
  do halt e lido depois sem timeout. Verificar: `step_frame(1, snapshot=true)` seguido de
  `3d.polygons` responde com `frame` igual ao quadro final e o mesmo `frame` numa segunda
  leitura. Se não vingar, reavaliar o design (captura fora do step).

## 1. Emulador — status e frame counter

- [x] 1.1 Adicionar `emu.status` ao `ControlServer`, atendido pela fila da EmuThread, com
  `running`/`halted`, `frame` atual, `snapshot_frame`/`age_frames`/`stale` (ou `null`).
  Verificar: com o alvo haltado por breakpoint, `emu.status` responde `halted=true` e o
  `frame` não muda entre chamadas.
- [x] 1.2 Incluir `frame` em todas as respostas de `3d.state`/`3d.polygons`/`3d.textures`.
  Verificar: o `frame` casa com o de `emu.status` para o snapshot em cache.

## 2. Emulador — captura atômica no step

- [x] 2.1 Estender `emu.step_frame` com `snapshot` (bool): armar o pedido de snapshot antes de
  rodar e consumi-lo no VBlank do **último** quadro, terminando parado. Verificar:
  `step_frame(10, snapshot=true)` termina em `halted` e o snapshot tem `frame == frame_final`.
- [x] 2.2 Sem `snapshot`, o comportamento atual permanece (nenhuma cópia). Verificar:
  `step_frame(10)` não preenche nem altera o cache existente.

## 3. Emulador — cache e `source`

- [x] 3.1 Guardar o último snapshot capturado (estado + polígonos + índice de texturas) como
  bloco imutável, com `frame`, compartilhado por `3d.state`/`3d.polygons`/`3d.textures`.
  Verificar: duas leituras consecutivas com `source=last` devolvem o mesmo `frame` mesmo com o
  emulador rodando.
- [x] 3.2 Implementar `source` (`auto` padrão, `last`, `fresh`) nas quatro leituras 3D e o
  fallback/erro com dica quando não há cache e o alvo está parado. Verificar: parado e sem
  cache → erro + `hint`; parado com cache → serve `last` com `age_frames=0`; `fresh` parado →
  erro + dica.
- [x] 3.3 Liberar/sobrescrever o cache sem vazar memória a cada nova captura. Verificar: N
  capturas seguidas mantêm o uso de memória limitado (um snapshot).

## 4. MCP

- [x] 4.1 Adicionar `emu_status()` em `tools/control.py`. Verificar: teste com canal fake
  devolve os campos e propaga erro.
- [x] 4.2 Adicionar `snapshot: bool = False` a `emu_step_frame` e repassar em
  `emu.step_frame`, ajustando o docstring para o fluxo "step+captura+halt". Verificar: teste
  com canal fake confirma o parâmetro no payload.
- [x] 4.3 Adicionar `source` (`last`/`fresh`/`auto`) a `gpu3d_state`/`gpu3d_polygons`/
  `gpu3d_textures`/`gpu3d_texture_dump`, repassando ao canal e documentando `frame`/
  `age_frames`/`stale`. Verificar: testes com canal fake cobrem os três valores e o erro com
  dica.

## 5. Documentação

- [x] 5.1 Atualizar a skill 3D (`references/concepts.md`/`display.md`) com o fluxo
  `emu_step_frame(n, snapshot=true)` → `gpu3d_* (source=last)` e a leitura de `frame`.
  Verificar: o inventário cita `emu_status` e `source`.

## 6. Validação

- [x] 6.1 Build do fork sem regressão; custo por quadro inalterado com nada ligado. Verificar:
  `cmake --build build -j` conclui; frame time sem captura ≈ baseline.
- [x] 6.2 MCP: `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` verdes.
- [x] 6.3 `openspec validate add-atomic-frame-snapshot --strict` verde.
- [ ] 6.4 Smoke real no KH: `emu_step_frame(N, snapshot=true)` até o letreiro → `gpu3d_state` e
  `gpu3d_polygons` com o **mesmo** `frame`, coerentes com `render_layer(engine=A, layer=3d)`,
  com o alvo parado. Verificar: os três batem e nenhuma chamada expira.
