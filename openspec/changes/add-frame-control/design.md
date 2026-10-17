## Context

Ver `proposal.md` — Why. O canal de controle já tem `emu.pause`/`emu.resume`
(`control-channel`), e a `EmuThread` já tem o maquinário de frame-step: `emuStatus_Running/
Paused/FrameStep`, a mensagem `msg_EmuFrameStep` (avança **1** quadro, via hotkey) e o laço
que roda **um quadro por iteração** (`RunFrame()` → `drawScreen()` → `handleMessages()`).
Falta avançar **N** quadros e **bloquear** até concluir. Este change é no **emulador
(frontend, `src/frontend/qt_sdl`)**, respeitando o modelo de threads.

## Goals / Non-Goals

**Goals:**
- `step_frame(N)` determinístico e bloqueante, terminando pausado com framebuffer composto.

**Non-Goals:**
- "Parar no próximo quadro" — já é o `emu.pause` (o `handleMessages()` roda após
  `drawScreen()`, então para no fim do quadro corrente).
- "Rodar até um evento" (framebuffer mudou, `PC`, condição) — é **condição**, dono é o
  `debug_resume`/watchpoint.
- Captura pausada, `render_layer`, DMA trace — changes separados.

## Decisions

- **Estender o frame-step existente com um contador** (`frameStepCount`), rodando um quadro
  por iteração até zerar — em vez de criar um laço próprio. Alternativa descartada:
  background thread — viola o modelo de threads.
- **Bloqueio por condição** (`frameStepPending` + `QWaitCondition`), acordada pela EmuThread
  quando o contador zera. Alternativa descartada: `waitAllMessages` sozinho — só garante que
  a mensagem foi consumida, não que os quadros rodaram.
- **Termina pausado** (como o frame-step atual): o agente inspeciona o frame parado; retoma
  com `emu.resume`.
- **Parada no vblank** com framebuffer composto (após `drawScreen`), habilitando captura/
  `render_layer` logo em seguida.
- **`run_until_vblank`/`pause_at_next_frame` NÃO são expostos**: o primeiro equivale a
  `step_frame(1)` (60 chamadas/s); o segundo já é `emu.pause`.
- **Contador/flag O(1) por quadro, sem alocação**, conforme a regra de carga mínima.

## Risks / Trade-offs

- [Interação com o stub GDB anexado] → parar o núcleo por frame-step com o gdb conectado
  pode conflitar; usar com o gdb desconectado (nota na doc).
- [Chamada concorrente a step] → chamadas são serializadas pela fila da EmuThread e o
  bloqueio por condição; a última vence.
