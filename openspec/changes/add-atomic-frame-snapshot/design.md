## Context

Ver `proposal.md`. Fatos da sessão de RE 3D (KH 358/2 Days):

- `3d.state`/`3d.polygons`/`3d.textures` pedem um snapshot **novo** no próximo VBlank. Com o
  gdb segurando a CPU, não há VBlank e a chamada expira (`3D snapshot timeout`).
- Cada chamada é um turno do agente. Entre `gpu3d_state` (frame 160686) e `gpu3d_polygons`
  (161006) passaram ~320 frames (~5 s) — os dois JSONs descrevem frames **diferentes**.
- `emu.step_frame(N)` já é atômico e termina parado (change `step-frame-with-debug`), mas não
  captura snapshot. Não há como pedir "ande até o letreiro e já me dê o 3D desse quadro".
- Não existe frame counter consultável com o alvo parado para alinhar/retomar.

## Goals / Non-Goals

**Goals:**

- Uma única operação **rodar N → capturar no VBlank alvo → haltar**, sem janela de latência.
- Ler o **mesmo** snapshot 3D com o alvo parado, com `frame`/idade, em vez de timeout.
- Expor o frame counter com o alvo parado.

**Non-Goals:**

- Ring buffer de snapshots por quadro; streaming contínuo por subscrição.
- Throttle/determinismo de fps (change posterior).
- Ler o framebuffer congelado da UI como fonte de snapshot.
- Alterar o formato de polígonos/texturas ou o decode.

## Decisions

- **Captura dentro do `step_frame`, não em chamada separada.** O pedido de snapshot é armado
  antes de rodar e consumido no `GPU3D::VBlank` do **último** quadro; a cópia acontece na
  EmuThread, no mesmo ponto consistente já usado pelo `add-3d-inspection` (depois de finalizar
  `RenderPolygonRAM`, antes de trocar `CurRAMBank`). Ao terminar, o alvo já está parado no
  frame capturado. Alternativa descartada: `emu.run_until_frame(N)` + `3d.*` depois — continua
  sendo duas idas e deixa o emulador rodar entre elas.

- **Cache de um snapshot, não de todos os frames.** Guardar um ring por quadro exigiria copiar
  estado+polígonos (até ~1–2 MB) **todo** quadro, violando a regra de custo O(1)/sem
  alocação por quadro. O cache é preenchido apenas quando um snapshot é pedido. Alternativa
  descartada: ring buffer por frame — custo por quadro inaceitável e sem assinante.

- **`source` com padrão `auto`.** `3d.state`, `3d.polygons` e `3d.textures` compartilham o
  snapshot em cache (mesmo `frame`), então chamadas consecutivas são coerentes mesmo com o
  emulador rodando. `fresh` força nova captura (exige rodar); `auto` captura só se não houver
  cache. Sem cache e parado: erro claro + dica `emu_step_frame(1, snapshot=true)`.
  Alternativa descartada: manter "sempre fresh" — é exatamente a causa da divergência entre
  chamadas. `last` fica para exigir coerência estrita (erro se o cache estiver vazio).

- **`age_frames` calculado no servidor.** `age = frame_atual - snapshot_frame`. Parado,
  `frame_atual == snapshot_frame` e `age == 0`; rodando, a idade cresce e `stale` sinaliza que
  o snapshot não é do quadro corrente.

- **Frame counter lido na EmuThread.** `emu.status` (e o `frame` das respostas) é respondido
  pela fila da EmuThread, evitando leitura rasgada de um contador de 64 bits e garantindo que
  o valor corresponde ao ponto de parada. Alternativa descartada: ler `NumFrames` direto da
  thread do socket — risco de corrida/torn read.

- **Texturas usam metadados do snapshot, texels vivos.** A lista `(TexParam, TexPalette)` vem
  do snapshot; o decode lê a VRAM de textura atual. Com o alvo parado no frame capturado isso é
  coerente; rodando, a textura pode ter mudado. Documentar no docstring; não copiar VRAM de
  textura por frame (custo).

- **MCP é passagem fina.** `emu_status` e `source` apenas repassam ao canal; a lógica de cache e
  seleção mora no `ControlServer`, não no Python. Mantém as camadas e evita duplicar estado.

## Risks / Trade-offs

- [Cópia do snapshot no VBlank do step] → limitada a `RenderNumPolygons` (≤2048) + vértices;
  one-shot, já é o comportamento do `add-3d-inspection`. Não roda por quadro.
- [Snapshot "velho" aceito por engano] → resposta sempre traz `frame`/`age_frames`/`stale`; o
  docstring recomenda `emu_step_frame(1, snapshot=true)` antes de confiar.
- [Textura viva × snapshot] → documentado; para coerência total, capturar com o alvo parado.
- [Frame counter na fila da EmuThread] → custo O(1) por chamada; nenhuma carga por quadro.
- [`fresh` com o alvo parado] → retorna erro + dica (não expira nem finge sucesso).

## Migration Plan

Aditivo. `emu.step_frame(n)` sem `snapshot` mantém o comportamento atual. `gpu3d_*` sem
`source` passa a servir `last` (com fallback para `fresh` quando há cache vazio e a máquina
roda) — o comportamento antigo deixa de ser o padrão e fica disponível em `fresh`. Atualizar a
skill e validar com `openspec validate --strict`, build do fork e `pytest`/`pyright`/
`lint-imports`.

## Open Questions

- `stale` deve ser booleano (`age > 0`) ou ter um limiar configurável (ex.: `age > 2`)? Iniciar
  booleano e revisar com uso real.
- `emu.step_frame(n, snapshot=true)` deve devolver o snapshot inline (economiza uma ida) ou só
  o `frame` e deixar `gpu3d_*` ler o cache? Preferir só metadados; medir se a ida extra
  incomoda.
