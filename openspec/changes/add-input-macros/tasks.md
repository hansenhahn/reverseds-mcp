## 1. Domínio

- [x] 1.1 Adicionar helper de domínio para tap e sequência (validação de passos, limite de tempo total) e verificar com um `ControlChannel` fake (ordem e durações)
- [x] 1.2 Garantir `input.release` no fim mesmo em erro (`finally`) e verificar com fake que lança no meio da sequência

## 2. Tools

- [x] 2.1 Expor `input_tap(mask, ms)` e verificar a alternância do menu (Start ou B)
- [x] 2.2 Expor `input_sequence(steps)` e verificar **Start→B** re-renderizando o HUD

## 3. Verificação

- [x] 3.1 Teste unitário com canal fake (sem emulador)
- [ ] 3.2 Teste de integração com o emulador (transição de menu observável por captura)

> Implementado no MCP (`domain/input.py` + tools). A verificação 3.2 depende do
> emulador com a imagem nova carregada.
