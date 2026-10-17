## 1. Hook no núcleo

- [x] 1.1 Adicionar um hook no início da transferência do cartucho (`WriteROMCnt` no start + `ROMCommandStart`) que registra `{addr, len, cmd}` e verificar que uma leitura de ROM gera um item
- [x] 1.2 Garantir custo zero com o trace desabilitado e verificar que nenhum item é coletado com o trace off

## 2. Batching

- [x] 2.1 Implementar o buffer pré-alocado com double-buffer e flush por N, e verificar que N itens geram um lote imediato
- [x] 2.2 Implementar o flush por timeout com lote parcial e verificar que itens pendentes são entregues após o timeout
- [x] 2.3 Garantir a ordem dos itens e o marcador de overflow no limite, e verificar que a ordem é preservada e que o overflow é sinalizado (sem descarte silencioso)

## 3. Canal de controle

- [x] 3.1 Expor `cart.trace.start {batch, timeout_ms}` e `cart.trace.stop` e verificar que iniciar passa a entregar lotes e parar encerra
- [x] 3.2 Entregar os lotes como notificação `event.cart` com os itens e verificar que um cliente recebe lotes com endereço/tamanho/comando

## 4. Verificação

- [x] 4.1 Verificar ponta-a-ponta que as leituras observadas batem com leituras reais do jogo (ex.: um load conhecido) e que a EmuThread só anexa/sinaliza (sem JSON/socket no caminho)
