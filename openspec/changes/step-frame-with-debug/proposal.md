## Why

Na depuração assistida quadro-a-quadro (ex.: uma animação), é preciso **avançar exatamente
`N` quadros e parar**, e inspecionar **sem latência** — o emulador **não pode** rodar quadros
soltos entre uma chamada e a próxima. Hoje há **dois "parado"** que não compõem:

- `emu.pause` (canal de controle) e o **halt do stub gdb**;
- o stub só é servido **com a CPU rodando** → com o emulador pausado, o debugger **não anexa
  nem lê** (o `debug_connect` trava);
- com o debugger **conectado**, o stub **segura a CPU** → o `emu.step_frame` **não avança**.

Resultado: não dá para "andar `N` quadros e inspecionar" de forma **frame-accurate**, que é
justamente o que uma sessão de RE precisa.

## What Changes

- **`emu.step_frame(N)` funciona com o debugger conectado**: avança **exatamente `N`** quadros
  e **cessa parado** — o mesmo "parado" que o debugger observa.
- **Parada unificada**: um **único** estado de "parado" (o do debugger); o stub é servido
  nesse estado e o `continue` retoma.
- **Remover `emu.pause`/`emu.resume`** (canal de controle + tools): parar = `step_frame`/halt;
  rodar = `continue`/`debug_resume`.
- Emulador (fork) + remoção de tools no MCP. **Não altera o comportamento de emulação.**

## Capabilities

### Modified Capabilities
- `frame-control`: avanço determinístico compatível com o debugger conectado (parada unificada).
- `control-channel`: remoção de `emu.pause`/`emu.resume`.

## Impact

- melonDS: EmuThread/stub gdb (o stub cede ao `step_frame` e o "parado" é o mesmo);
  ControlServer (remover `emu.pause`/`emu.resume`).
- MCP: remover as tools `emu_pause`/`emu_resume`; o `emu.step_frame` permanece (é o avanço
  atômico).
- **Spike primeiro**: a interação stub ↔ FrameStep ↔ threads é o ponto de risco; validar o
  mecanismo antes de implementar.
