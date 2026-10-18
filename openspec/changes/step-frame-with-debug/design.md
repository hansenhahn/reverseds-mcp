## Context

Ver `proposal.md`. Hoje a "parada" existe em **dois lugares**: o `emuStatus` da `EmuThread`
(`emu.pause`; e o `step_frame` termina em `emuStatus_Paused`) e o **stub gdb**, que decide, no
laço da CPU (`RunFrame<InterpreterGDB>`), se ela avança. Eles **não conversam**: o stub só é
servido quando a CPU roda.

## Goals / Non-Goals

**Goals:**
- `step_frame(N)` frame-accurate **com o debugger conectado**, terminando num estado
  inspecionável (o "parado" do debugger).

**Non-Goals:**
- Non-stop completo; breakpoints/watchpoints (inalterados); modelo de input.

## Decisions

- **Um único "parado"**: o estado de parada da emulação e o "stopped" do stub passam a ser
  **o mesmo**. Enquanto parado, a EmuThread **serve o stub** (como o hook `HaltService` já faz
  quando o stub segura a CPU); e um `continue` **desfaz** a parada.
- **`step_frame` é o avanço atômico (e o "stop")**: roda `N` quadros **dentro** da EmuThread e
  para. Com o debugger conectado, o stub **cede** durante o avanço e volta a segurar no fim
  (o mesmo parado) — assim o cliente faz **uma** chamada e cai no quadro `N` **já parado**,
  **sem janela de latência**.
- **Remover `emu.pause`/`emu.resume`**: o agente não pausa pelo canal; ele **avança**
  (`step_frame`) e o **debugger** para/roda.
- **Inspeção em parado**: já verificada — mem/regs via gdb, captura/render/IO via canal.

## Risks / Trade-offs

- [Interação de threads] → stub e FrameStep rodam na **mesma** thread (EmuThread); o trabalho
  é O(1). **Spike obrigatório** antes da implementação.
- [O pause do frontend ≠ halt] → o pause do menu do frontend continua existindo; só o
  **caminho do agente** muda (para o halt).
