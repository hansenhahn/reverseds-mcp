## Context

Ver `proposal.md` — Why. Estado atual:

- `EmuThread::emuReset()`/`msg_EmuReset` já existem (reset via `EmuInstance::reset` →
  `NDS::Reset`), mas o canal de controle não os expõe. `ARM::Reset` **não** limpa
  `GdbStub.BpList/WpList`, então os breakpoints/watchpoints sobrevivem ao reset.
- `GdbStub::CheckBkpt/CheckWatchpt` sempre entram no stub (param) quando há hit. Não há
  registro de hits sem interromper.
- `CheckWatchpt` só é chamado no caminho de acesso da CPU (`ARM::GdbCheckD`, modo
  `InterpreterGDB`). DMA escreve via `NDS::ARM9Write16/32`/`ARM7Write16/32`, sem passar por
  esse check.
- O `ControlServer` já acessa `instance->getNDS()` e `nds->ARM9`/`ARM7` (públicos), então
  pode falar com o `GdbStub` de cada core.

## Goals / Non-Goals

**Goals:**
- `emu.reset` determinístico, preservando BPs/WPs e parando em um ponto de boot determinístico com gdb.
- Hit log por core, com ring buffer, sem parar; leitura/limpeza/start/stop.
- Watchpoint de write/access também dispara em DMA; com log, registra o PC do programador.
- Tools MCP e testes; nenhum custo quando não há watchpoint/log.

**Non-Goals:**
- Watchpoint por unidade de DMA (a checagem é por faixa/slice).
- Persistir o hit log em disco ou entre sessões.
- Mudar o protocolo GDB; a API é do canal de controle.
- UI.

## Decisions

- **Reset reusa `EmuThread::emuReset`.** `emu.reset` chama
  `instance->getEmuThread()->emuReset()` e espera a mensagem. O `NDS::Reset` mantém o cartucho
  e não mexe em `BpList/WpList`; com gdb anexado, o stub continua parado em um ponto de boot determinístico e o agente decide
  quando `debug_resume`. Alternativa: resetar no control thread — violaria a EmuThread.
- **Hit log dentro do `GdbStub`.** `HitRecord{pc,addr,kind}` em `std::deque` com capacidade
  fixa, `std::mutex` e flag atômica. `CheckBkpt`/`CheckWatchpt`, com o log ligado, registram e
  retornam `CheckNoHit` (CPU continua). Sem o log, comportamento atual. O ring conta
  `dropped` quando descarta o mais antigo.
- **O hit log não substitui o stop.** `gdb.hits.start` liga o modo log; se o agente quiser
  parar, desliga o log ou usa `debug_wait` com o log desligado.
- **DMA: check por faixa/slice.** Após cada `DMA::Run9/Run7`, calcula-se a faixa de destino
  efetivamente escrita (`min..max`, ou uma unidade se o incremento é 0) e chama
  `NDS::GdbCheckDmaWrite(cpu, lo, len, ProgramPc)`. O check percorre no máximo os 4 WPs e
  retorna cedo se a lista está vazia. Alternativa: checar por unidade — custo alto.
- **DMA hit usa o PC do programador.** `DMA::ProgramPc` acompanha a chamada; no hit log o
  `pc` registrado é o programador (o stop gdb normal mostra o PC da CPU no momento). O agente
  usa `dma_trace` se precisar de `src/dst`.
- **Controle acessa o stub por core.** `gdb.hits.*` recebe `core` (`arm9`/`arm7`) e chama
  `nds->ARM9->GdbStub`/`nds->ARM7->GdbStub`; os métodos do stub são thread-safe. Tudo sob
  `#ifdef GDBSTUB_ENABLED`; sem o stub, o canal responde `method not found`.
- **MCP fino sobre o canal.** `emu_reset` e `hit_log_*` chamam `control.call`; `hit_log_read`
  formata `pc`/`addr` em hex e mapeia `kind` para nome. Alternativa: lógica no MCP — o ring
  precisa morar no stub, ao lado do check.

## Risks / Trade-offs

- [Reentrância: stop da DMA dentro do `DMA::Run`] → `Enter` já é usado pelo caminho da CPU;
  o DMA só chama depois do slice, com o estado consistente; smoke real obrigatório.
- [Hit log enche em loop] → ring fixo + `dropped`; o agente lê/limpa.
- [Reset com gdb parado] → `HaltService` processa a mensagem; validar que o PC vai a um ponto de boot determinístico e
  os BPs continuam; se o stub não responder, reiniciar o melonDS.
- [Concorrência do ring] → mutex no start/stop/read/clear/record.
- [DMA de faixa grande gera hit em endereço vizinho] → o hit registra o endereço do WP
  (não o offset exato); suficiente para causalidade, documentado.

## Migration Plan

Aditivo. `emu.reset`/`gdb.hits.*` só existem com GDB stub compilado. Sem watchpoints e sem log,
o check de DMA é uma chamada barata por slice. Atualizar testes MCP, skill e validar com
`pytest`/`pyright`/`lint-imports`, `openspec validate --strict`, build do fork e smoke real
(reset com BP; hit log; DMA em VRAM).

## Open Questions

- Expor `dma.hit` como evento assíncrono no canal? (Fica para a Onda 2/streaming.)
- Limitar o hit log por endereço/PC? (Não nesta versão; ring + dropped basta.)
