## Context

Ver `proposal.md`. Falhas observadas na sessão de RE 3D:

- Slot 10 salvo no letreiro com o gdb conectado; ao carregar, veio a **cena da prisão**.
  `savestate_save` retornou `ok` sem validar nada.
- Slot 1 carregado com o gdb anexado (+600 frames) parou no logo da KH, diferente do mesmo
  slot carregado desconectado. A doc do próprio MCP alerta para carregar o estado antes de
  conectar o gdb.
- Slots numéricos são compartilhados com hotkeys/UI; não há dono, lock nem metadados.

O que já existe: o change `step-frame-with-debug` unificou o "parado" (stub gdb) e o
`ControlServer` atende operações de controle com o alvo haltado. O savestate em si continua
sem verificação e sem metadados.

## Goals / Non-Goals

**Goals:**

- Impossibilitar o "ok silencioso": salvar/carregar só reporta sucesso após integridade e
  round-trip.
- Detectar slot sobrescrito por fora (UI/outra sessão) antes de carregar.
- Savestates nomeados, com dono e lock, sem quebrar os slots numéricos da UI.

**Non-Goals:**

- Mudar o formato binário do savestate do melonDS (deve continuar abrindo na UI).
- Snapshot/captura 3D (ver `add-atomic-frame-snapshot`).
- Criptografia ou compressão; `crc32` é detecção de corrupção, não segurança.

## Decisions

- **Sidecar, não header no binário.** Alterar o formato do savestate quebraria a
  compatibilidade com a UI e com estados existentes. Um arquivo `.re.json` ao lado guarda
  hash, frame, PC, dono e rótulo; o binário permanece nativo. Alternativa descartada: envelopar
  o estado — quebra o ecossistema do melonDS por pouco ganho.

- **Validação pré-load, não rollback.** Não há como "carregar em sombra" o estado no melonDS
  sem duplicar toda a máquina; então validamos **antes** de aplicar (existência do sidecar,
  gamecode, tamanho, crc32). Se passar, aplica e faz round-trip. Alternativa descartada:
  carregar e tentar desfazer — caro e arriscado.

- **Round-trip com frame + PC.** O contador de frames vem do `emu.status` do change
  `add-atomic-frame-snapshot` (ou da leitura existente na EmuThread enquanto ele não entra);
  o PC só é comparável com o gdb anexado. Divergência vira `verified=false` + aviso, não
  `ok` silencioso.

- **Gravação atômica + hash.** Escrever em `.tmp`, calcular `crc32` do arquivo final, `rename`
  atômico e então gravar o sidecar (`.tmp` + rename). Assim nunca existe sidecar apontando para
  um estado pela metade. Alternativa descartada: gravar direto no slot — deixa estado parcial
  se houver crash.

- **Nomear = namespace dedicado no diretório do emulador.** O canal aceita `name` além de
  `slot` (e `path`, mantido para uso direto); `name` é sanitizado (`[A-Za-z0-9._-]`, sem `..`,
  não numérico) e resolvido para `savestate_named_<name>.sav` no diretório de savestates do
  emulador, fora da numeração da UI (`savestate_<n>.sav`). O MCP só repassa o nome — não
  precisa enxergar o filesystem do emulador (roda em contêiner). Alternativa descartada:
  mapear nome para um slot numérico reservado — continua colidindo com a UI.

- **Dono + lock.** O sidecar registra `owner` (id da sessão MCP) e `label`. Um lock `flock` no
  arquivo de estado impede escrita concorrente; `load` de um `owner` diferente exige
  `force=true`. Alternativa descartada: lock global — serializa demais e não identifica dono.

- **Detecção de clobber na listagem.** Comparar o `crc32`/tamanho atuais do binário com o
  sidecar; divergência indica que outro processo escreveu no slot. Alternativa descartada:
  confiar só em mtime — não detecta reescrita idêntica nem corrupção.

- **Mid-frame é aviso, não bloqueio.** Um breakpoint pode parar no meio de um quadro; o
  savestate do melonDS ainda é aplicável, mas o snapshot 3D/captura não. Registrar
  `mid_frame=true` com dica de `emu_step_frame` para um limite de frame, sem impedir o save.

## Risks / Trade-offs

- [Sidecar ausente em estados antigos] → carregar mesmo assim, com `verified=false` e aviso
  (não erro), preservando compatibilidade.
- [Gamecode diferente] → bloquear o load (evita exatamente o "estado de outro jogo/cena").
  Requer ROM correta carregada; erro acionável.
- [Hash caro] → `crc32` de poucos MB é rápido e roda **fora** da EmuThread (thread do
  cliente), no save/load, não por quadro.
- [Race entre validação e load] → lock `flock` mantido durante validação + load.
- [`pc` não comparável sem gdb] → só validar `pc` quando o debugger estiver anexado; caso
  contrário validar só `frame`/hash.
- [Nome nomeado] → sanitizar no canal (rejeitar `..`, separadores e nomes puramente
  numéricos) e derivar o caminho a partir do diretório de savestates do emulador.

## Migration Plan

Aditivo. Slots numéricos continuam idênticos; o sidecar nasce na primeira gravação feita por
esta versão. Estados antigos carregam com `verified=false` (aviso). Atualizar a skill e
validar com `openspec validate --strict`, build do fork, `pytest`/`pyright`/`lint-imports` e
um smoke de save→load com o gdb conectado.

## Open Questions

- O `owner` deve ser estável entre reinícios do MCP (ex.: derivado do socket) ou por sessão?
  Iniciar por sessão; se atrapalhar, promover a dono de máquina.
- Guardar o sidecar ao lado do estado (mesmo diretório) para sobreviver à UI e ao
  reinício do MCP; validar no smoke.
