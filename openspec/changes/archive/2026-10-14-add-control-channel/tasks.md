## 1. Fundação do canal

- [x] 1.1 Vendorar `nlohmann/json` (header-only) no repo e confirmar que o build do melonDS continua compilando
- [x] 1.2 Criar o módulo `ControlServer` na camada `qt_sdl` com socket Unix domain (path configurável; TCP opcional desligado) e verificar que o socket é criado ao iniciar o emulador (conectar com `socat - UNIX-CONNECT:<path>`)
- [x] 1.3 Implementar o framing `Content-Length: <N>\r\n\r\n<body>` (leitura e escrita) e verificar com teste de ida/volta para payloads de tamanhos variados
- [x] 1.4 Implementar o dispatch JSON-RPC 2.0 (request/response/error/notification) e verificar com um método `ping` (resultado) e um método inexistente (erro de método não encontrado)
- [x] 1.5 Adicionar a thread de socket e a fila de requisições para a EmuThread e verificar que uma requisição é atendida sem travar a emulação (frame rate estável durante a chamada)

## 2. Input

- [x] 2.1 Expor o método `input.key` (máscara active-low) reusando `NDS::AgentInputMask`/`SetKeyMask` e verificar que o `KEYINPUT` (0x04000130) reflete o mask injetado
- [x] 2.2 Expor `input.touch` e `input.release` e verificar via `EXTKEYIN` (0x04000136, lido pelo ARM7) que a caneta fica pressionada/solta
- [x] 2.3 Expor `input.merge on/off` e verificar que, desligado, o input do host não interfere no estado injetado, e ligado, humano e agente se somam
- [x] 2.4 Estender o teste de input (cliente Python) cobrindo `input.key`/`input.touch`/`input.release` e verificar que passa

## 3. Tela

- [x] 3.1 Implementar `screen.capture` retornando as telas superior e inferior com dimensões e verificar pixels não-vazios
- [x] 3.2 Implementar o frame binário `[u32 BE N][bytes]` anunciado pelo JSON-RPC e verificar que um cliente Python lê exatamente N bytes e reconstrói a imagem
- [x] 3.3 Garantir a captura sob o renderer de software e verificar que, no renderer OpenGL, o método retorna um erro claro (limitação documentada)
- [x] 3.4 Parametrizar `screen.capture` (telas + formato) e verificar que `rgba8` retorna 8 bits por canal com a composição preservada
- [x] 3.5 Implementar o streaming parametrizável (intervalo + duração/nº de amostras) e verificar que "1000 ms por 10000 ms" entrega 10 amostras sem capturar os quadros intermediários
- [x] 3.6 Fazer a conversão BGRA→RGBA fora da EmuThread e verificar que a EmuThread só copia o framebuffer quando uma amostra é devida

## 4. Savestate e execução

- [x] 4.1 Expor `savestate.save`/`savestate.load` roteando pela fila da EmuThread e verificar que salvar e carregar restaura um estado observável
- [x] 4.2 Expor `emu.pause`/`emu.resume` e verificar que o pause congela o avanço e o resume retoma

## 5. Documentação

- [x] 5.1 Documentar o canal de controle no `melonds-gdb-debugging.md` (referência pro MCP) e verificar que o script de demonstração (`nds-control.sh`) roda
