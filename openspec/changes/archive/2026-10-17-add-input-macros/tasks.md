## 1. Domínio

- [x] 1.1 Adicionar helper de domínio para tap e sequência (validação de passos, limite de tempo total) e verificar com um `ControlChannel` fake (ordem e durações)
- [x] 1.2 Garantir `input.release` no fim mesmo em erro (`finally`) e verificar com fake que lança no meio da sequência
- [x] 1.3 Generalizar `InputStep` para aceitar **toque** `(x, y)` (mutuamente exclusivo com `mask`) + validação de coordenadas (`0<=x<256`, `0<=y<192`); verificar com fake

## 2. Tools

- [x] 2.1 Expor `input_tap(mask, ms)` e verificar a alternância do menu (Start ou B)
- [x] 2.2 Expor `input_sequence(steps)` e verificar **Start→B** re-renderizando o HUD
- [x] 2.3 Expor `input_touch_tap(x, y, ms)` e `input_sequence` aceitando passos de toque (intercaláveis com botões)

## 3. Verificação

- [x] 3.1 Teste unitário com canal fake (sem emulador)
- [x] 3.3 Teste unitário do toque com canal fake (tap e passo de sequência)
- [x] 3.2 Teste de integração com o emulador: `input_touch_tap` num ponto da tela de baixo (Hotel Dusk, touch-only) transiciona o jogo, observável por captura (pixels mudam)

> Implementado no MCP (`domain/input.py` + tools). O 3.2 foi verificado no emulador real
> (controle + captura) pelo caminho tool→serviço→canal.
