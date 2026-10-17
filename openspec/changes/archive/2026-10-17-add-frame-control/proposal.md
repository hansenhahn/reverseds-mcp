## Why

A sessão de RE do Hotel Dusk patinou porque **não dá para congelar um frame exato**: o
`debug_connect` tem latência e o frame já avançou; sem frame-step, o frame-alvo não pôde
ser observado de forma determinística — e watchpoints/diffs ficaram reféns disso.

## What Changes

- `emu.step_frame(N)`: pausa, avança exatamente `N` quadros (`N ≥ 1`) e **para**, com o
  framebuffer do último quadro já composto; **bloqueia até concluir**. Avançar N numa
  chamada evita o anti-padrão de passo-a-passo a 60 Hz pelo canal de controle.
- A parada SHALL ocorrer no **vblank**, com o framebuffer composto (pronto para captura).
- "Parar no próximo quadro" **não** entra aqui: já é coberto pelo `emu.pause` existente,
  que para no fim do quadro corrente (o `handleMessages()` roda após `drawScreen()`).
- "Esperar o próximo vblank" é **primitivo interno**, não uma tool.
- Emulador (fork) expondo o método no canal de controle; tool MCP correspondente.
- **Não altera o comportamento de emulação**; sem custo por quadro quando não usado.

## Capabilities

### New Capabilities
- `frame-control`: avanço determinístico de quadros, sincronizado ao vblank.

### Modified Capabilities
<!-- nenhuma -->

## Impact

- melonDS: novo método no canal de controle (frontend), aplicado na **EmuThread** via a
  fila de mensagens; o laço de quadro para no vblank.
- MCP: tool fina que chama o canal.
- Custo adicional por quadro SHALL ser desprezível sem uso.
