## Why

A sessão de RE da animação do Hotel Dusk deixou lacunas que atrapalham fechar o loop com
confiança: a captura pode "não capturar" **silenciosamente**; não há como pedir **backtrace**
nem **listar breakpoints** ao gdb; o trace de DMA **perde o core** (`cpu`) que o emulador já
envia; o `pc` registrado no DMA é o `R[15]` pós-incremento, não a instrução que programou o
canal; e **não há logs** — quando algo quebra (ex.: o gdb cai e `health_check` estoura
`BrokenPipeError`), `./deploy.sh logs` só mostra um traceback cru, sem contexto (tool, argumentos,
estado dos backends). Sem isso, o agente não consegue ir do "o dado está na VRAM" até "o código
que o colocou lá" com segurança, nem diagnosticar uma sessão quebrada.

## What Changes

- `screen_capture`: quando a captura decodifica **0 frames**, o MCP SHALL retornar `error`
  (com `hint`) — nunca `{"paths": []}` silencioso.
- Novas tools de depuração: `debug_backtrace` (`bt`) e `list_breakpoints`, expostas pelo stub
  GDB, com um resultado tipado (frames com `#`, `pc`, `function`; breakpoints com número,
  tipo, endereço, condição e se está habilitado).
- `dma_trace`: cada item SHALL incluir o **`cpu`** (ARM9/ARM7) — o emulador já o envia; e o
  `pc` SHALL ser o endereço da **instrução que programou o canal** (o store em `DMAxCNT`), não
  o valor cru de `R[15]`.
- Emulador: corrigir a captura do `pc` do DMA (deduzir a instrução do store a partir do modo
  ARM/Thumb) sem alterar o comportamento de emulação.
- **Logging estruturado** no MCP (nível configurável via `RE_MCP_LOG_LEVEL`, para `stderr`,
  capturável por `deploy.sh logs`): início/config, conexão/reconexão do canal, ciclo de vida
  do gdb, cada chamada de tool (nome, duração, ok/erro) e erros com contexto — sem segredos
  nem payloads grandes.
- **Logging no canal de controle** (emulador): requisição/erro com método, `id` e duração,
  conexão/desconexão de cliente, com nível configurável e **fora da thread de emulação**.
- **Backend morto não derruba a tool**: quando o gdb (ou o canal) morre no meio de uma
  operação, a tool SHALL retornar `{"error", "hint"}` (ex.: reconectar) em vez de deixar a
  exceção escapar; o backend SHALL marcar-se desconectado e a próxima chamada reconecta.
- **Acesso serializado ao backend**: chamadas de tool concorrentes (o servidor roda as tools
  síncronas em thread pool) SHALL ser serializadas por backend (um lock), de modo que duas
  chamadas nunca intercalem I/O no mesmo gdb/canal. Hoje, ler vários registradores em paralelo
  mistura escritas/leituras e desincroniza/quebra a sessão — provável causa da queda do gdb.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `dma-trace`: o item decodificado passa a incluir `cpu` e o `pc` com a semântica da instrução
  que programou o canal.
- `mcp-debug-tools`: adiciona `debug_backtrace` e `list_breakpoints`.
- `mcp-control-tools`: captura com 0 frames decodificados passa a ser erro explícito.
- `mcp-bridge`: adiciona logging estruturado do MCP e garante que um backend morto vire
  `error` + `hint` (sem exceção).
- `control-channel`: adiciona logging do canal de controle (requisições/erros/conexões, fora
  da thread de emulação).

## Impact

- MCP: `domain/io/dma.py` (`DmaTransfer` + `cpu`, semântica do `pc`),
  `application/dma_trace.py`, `tools/control.py` (`_dma_dict`, `screen_capture`, `health_check`),
  `application/ports/debug.py` (novos métodos), `infra/gdb.py` (parse de `bt`/`info
  breakpoints`, queda do gdb → `DebugError`, logs), `infra/control.py` (logs), `tools/debug.py`
  (novas tools), `__main__.py`/config (nível de log).
- Emulador: `src/DMA.cpp`/`src/NDS.cpp` (origem do `pc`), `src/frontend/qt_sdl/ControlServer.cpp`
  (já envia `cpu`; adiciona logging do canal com nível configurável).
- Sem mudança de comportamento de emulação; sem custo por quadro.
