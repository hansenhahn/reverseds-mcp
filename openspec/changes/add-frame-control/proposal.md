## Why

A sessão de RE do Hotel Dusk patinou porque **não dá para congelar um frame exato**: o
`debug_connect` tem latência e o frame já avançou; sem frame-step, o frame-alvo não pôde
ser observado de forma determinística — e watchpoints/diffs ficaram reféns disso. Todos
os outros primitivos de observação dependem de parar num frame conhecido.

## What Changes

- `emu.step_frame(N)`: avança exatamente N quadros e **para**, com o framebuffer do
  último quadro já composto.
- `emu.run_until_vblank()`: roda até o próximo **vblank** e para (framebuffer composto).
- `emu.pause_at_next_frame()`: agenda uma parada no fim do quadro atual.
- A parada SHALL ocorrer no **vblank**, com o framebuffer composto (pronto para captura).
- Emulador (fork) expondo os métodos no canal de controle; tools MCP correspondentes.
- **Não altera o comportamento de emulação**; sem custo por quadro quando não usado.

## Capabilities

### New Capabilities
- `frame-control`: avanço determinístico de quadros e parada sincronizada ao vblank.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- melonDS: novos métodos no canal de controle (frontend), aplicados na **EmuThread** via
  a fila de mensagens; o laço de quadro para no vblank.
- MCP: tools finas que chamam o canal.
- Custo adicional por quadro SHALL ser desprezível sem uso.
