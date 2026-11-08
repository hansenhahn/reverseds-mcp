## Why

A depuração 3D frame-accurate falha por **corrida**, não por falta de dados. O snapshot 3D
só existe no VBlank e só é copiado quando pedido; com o alvo haltado, não há VBlank e
`3d.*` expira. Além disso, não há operação atômica "rodar N quadros → capturar → haltar":
cada tool é um turno separado, e o emulador roda solto entre eles (o cartão de título de
poucos segundos é perdido). Também não há como saber **em que frame** o alvo está parado.

Resultado observado: `gpu3d_state` e `gpu3d_polygons` descrevem frames diferentes; com o
debugger parado, `gpu3d_*` retorna timeout; e o agente não consegue alinhar/retomar num frame
exato.

## What Changes

- **`emu.status`**: devolve `running`/`halted`, o **frame counter** atual e o frame do último
  snapshot em cache (com `age_frames`/`stale`), legível **com o alvo parado**.
- **`emu.step_frame(n, snapshot=false)`**: quando `snapshot=true`, arma a captura, roda
  exatamente `N` quadros e copia o snapshot 3D **no VBlank do quadro alvo**, tudo na mesma
  chamada (uma única ida ao canal), terminando parado. Elimina a corrida entre turnos.
- **Snapshot em cache, compartilhado e imutável**: `3d.state`, `3d.polygons` e `3d.textures`
  passam a aceitar `source` (`auto` padrão, `last`, `fresh`); reusam o **mesmo**
  snapshot (mesmo `frame`), mesmo com a CPU parada, em vez de tirar um novo a cada chamada e
  divergir. Sem cache e parado, retornam erro + dica acionável.
- **MCP**: nova tool `emu_status`; `emu_step_frame(n, snapshot=...)`; `gpu3d_*` com `source`;
  docstrings com o fluxo atômico.
- **Custo**: a captura continua **on-demand** (sem cópia por quadro); o cache guarda apenas o
  último snapshot pedido.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `frame-control`: avanço `N` quadros pode capturar o snapshot 3D no VBlank alvo na mesma
  operação; novo status/frame counter consultável parado.
- `control-channel`: adiciona `emu.status`, `snapshot` em `emu.step_frame` e `source` em
  `3d.state`/`3d.polygons`/`3d.textures`/`3d.texture` com cache do último frame.
- `mcp-control-tools`: adiciona `emu_status` e o parâmetro `snapshot` em `emu_step_frame`.
- `mcp-3d-tools`: `gpu3d_*` aceitam `source` e expõem `frame`/`age_frames`/`stale`.

## Impact

- Emulador: `src/frontend/qt_sdl/ControlServer.{h,cpp}` (status, captura no step, cache do
  snapshot, seleção `source`); reuso do snapshot one-shot de `GPU3D::VBlank` já existente.
- MCP: `tools/control.py` (`emu_status`, `emu_step_frame`), `tools/three_d.py` (`source`),
  `tools/server.py`, testes com canal fake.
- Não altera o comportamento de emulação; nenhuma cópia por quadro; leitura de cache é O(1)
  após a captura.
- Fora de escopo: ring buffer de snapshots por frame, throttle/determinismo e leitura do
  framebuffer congelado do viewer (ver `design.md`, alternativas descartadas).
