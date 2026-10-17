## Context

Ver `proposal.md` — Why. Hoje o canal de controle só tem `emu.pause`/`emu.resume`
(`control-channel` spec); não há granularidade de quadro. O fork já usa a **fila de
mensagens da EmuThread** para operações de núcleo (input, savestate, captura), e o laço de
emulação (`EmuThread`) conhece os eventos de LCD (HBlank/vblank). O parar "por gdb" não
serve: o gdb não avança frames nem garante framebuffer composto. Este change é no
**emulador (frontend, `src/frontend/qt_sdl`)**, respeitando o modelo de threads.

## Goals / Non-Goals

**Goals:**
- Avanço determinístico de quadros e parada no vblank com framebuffer composto.

**Non-Goals:**
- Captura pausada (`add-paused-capture`), `render_layer` (`add-layer-render`),
  DMA trace (`add-dma-trace`) — changes separados.
- Controle de velocidade (slow motion/turbo).

## Decisions

- **Reusar a fila de mensagens da EmuThread** (padrão existente) para agendar a parada;
  nada de mecanismo novo. Alternativa descartada: thread própria — viola o modelo.
- **Parar no vblank**, não em ponto arbitrário: é quando o framebuffer está composto,
  habilitando captura/`render_layer` logo em seguida. Alternativa descartada: parar no
  HBlank — framebuffer incompleto.
- **Contador de quadros + flag de parada O(1) por quadro, sem alocação**, conforme a regra
  de carga mínima do canal de controle.
- **Gatilho por mensagem** (`emu.step_frame`/`run_until_vblank`/`pause_at_next_frame`),
  respondendo quando a parada ocorre (fora da thread de emulação).

## Risks / Trade-offs

- [Latência da resposta até a parada] → a resposta chega no vblank seguinte; documentado e
  suficiente para RE.
- [Interação com o stub GDB anexado] → parar o núcleo avança o frame; a ferramenta deve
  ser usada com o gdb desconectado ou ciente (nota na doc).
