## 1. Diagnóstico e erros

- [x] 1.1 Adicionar helpers de erro (`_error`, `_debug_error`, hint no `_control`) e aplicar nas tools (contrato `{"error","hint"?}`)
- [x] 1.2 Expor `health_check()` (canal + debugger) e verificar com o emulador ligado/desligado
- [x] 1.3 `debug_connect()` faz read de teste pós-conexão e falha com hint; verificar com stub morto

## 2. Snapshots

- [x] 2.1 `mem_snapshot` persiste `.bin`+`.json` em `RE_MCP_OUT_DIR/snapshots` e verificar os arquivos
- [x] 2.2 `state_diff` carrega do disco quando não há em RAM; verificar após “restart” (limpar a RAM)

## 3. Captura

- [x] 3.1 `screen_capture` retorna hint quando expira (CPU haltada/renderer) e verificar com a CPU parada

## 4. Verificação

- [x] 4.1 Teste de descoberta das tools (`health_check`) e teste unitário dos helpers de erro

> Implementado no MCP. A verificação "ao vivo" (emulador ligado/desligado, CPU parada) depende
> de carregar a imagem nova e será feita na próxima sessão de depuração.
