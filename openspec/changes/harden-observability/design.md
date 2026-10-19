## Context

Ver `proposal.md` — Why. Pontos do estado atual que moldam o approach:

- O MCP é hexagonal; o backend de debug (`infra/gdb.py`) é um **parser de texto** sobre
  `gdb-multiarch` (sem MI), e as tools expõem `{"error", "hint"?}`.
- O emulador já envia `cpu` no evento de DMA (`ControlServer.cpp`), mas
  `DmaTrace.collect`/`DmaTransfer.from_raw` **descartam** o campo.
- O `pc` do DMA vem de `DMA::WriteCnt` → `NDS::GetPC(CPU)` = `R[15]` **já incrementado**
  (endereço da instrução seguinte), não da instrução do store.
- `save_framebuffer_pngs` devolve `{"paths": []}` quando o payload decodifica 0 frames.
- **Não há logging**: o MCP não usa `logging`; quando o gdb cai, `_cmd` escreve num pipe
  quebrado e o `BrokenPipeError` escapa da tool (`health_check`), virando erro inesperado no
  log do uvicorn — sem contexto de tool/backend. O `ControlServer` também não loga tráfego.
- Os access logs do uvicorn (um POST por chamada) são ruído e não substituem logs de domínio.
- **Sem lock nos backends**: `GdbBackend._cmd` e `UnixControlChannel.call` escrevem/leem no
  mesmo processo/socket sem serialização; o servidor MCP roda as tools síncronas em **thread
  pool** (`anyio.to_thread.run_sync`), então chamadas paralelas disputam o mesmo I/O → escritas
  intercaladas, um consumindo o prompt/resposta do outro, e queda/`BrokenPipe`.

## Goals / Non-Goals

**Goals:**
- Captura sem frames vira **erro explícito** (com `hint`).
- `debug_backtrace` e `list_breakpoints` no stub gdb, tipados no MCP.
- Item de DMA com **`cpu`** e `pc` da **instrução que programou** o canal.
- Sem mudança de comportamento de emulação e sem custo por quadro.

**Non-Goals:**
- gdb MI / reescrita do parser; non-stop; resolução de símbolos além do que o gdb já dá.
- Alterar o payload do evento de DMA (o `cpu` já está lá).
- UI/cliente.

## Decisions

- **Captura vazia → erro na tool, não no encoder.** `save_framebuffer_pngs` continua um
  encoder puro; `screen_capture` checa `paths == []` e devolve `error` + `hint`. Alternativa:
  levantar no helper — misturaria transporte com codificação de imagem.
- **`DmaTransfer.cpu: int` + serialização `"arm9"`/`"arm7"`.** `from_raw(cpu, ch, src, dst,
  cnt, pc)`; `collect` passa `raw["cpu"]`; `_dma_dict` mapeia `0→arm9`, `1→arm7`. Domínio
  tipado; saída amigável ao agente. Alternativa: expor o int cru (menos legível).
- **`pc` do DMA = endereço da instrução do store.** Em `DMA::WriteCnt`, usar
  `R[15] - ((CPSR & 0x20) ? 2 : 4)` — o mesmo idioma já usado no melonDS (JIT/fault em
  `ARM.cpp`). Alternativa: rastrear o endereço da instrução explicitamente no interpretador
  (mais invasivo). Limitação: em Thumb‑2 (32 bits) o cálculo pode apontar 2 bytes dentro da
  instrução; validar por desassemblagem e documentar.
- **Backtrace/list como texto tipado no adaptador.** Estender a porta `Debugger` com
  `backtrace()` e `breakpoints()`, retornando objetos de domínio (`StackFrame`, `Breakpoint`)
  parseados de `bt` e `info breakpoints`. Mantém o estilo do backend (texto) e o contrato
  tipado na borda. Alternativa: gdb MI (fora de escopo).
- **Tools no estilo existente**: `debug_backtrace`, `list_breakpoints`, com erro claro quando
  o alvo está rodando.
- **Logging do MCP via `logging` para `stderr`.** Um logger `re_mcp` com nível de
  `RE_MCP_LOG_LEVEL` (default `INFO`), formatação com timestamp/nível/logger/mensagem e campos
  de contexto (`event`, `tool`, `duration_ms`, `backend`, `error`). Um wrapper nas tools loga
  nome/duração/ok-erro sem tocar no payload; `infra/control.py` e `infra/gdb.py` logam
  conexão/reconexão/queda. Access logs do uvicorn podem ser reduzidos independentemente.
  Alternativa: JSON puro (mais legível por máquina, pior no `docker logs`) — formato `key=value`
  como meio-termo.
- **Queda do backend vira erro de domínio.** Em `GdbBackend._cmd`, capturar
  `BrokenPipeError`/`OSError` na escrita e na leitura, marcar `_proc=None` e levantar
  `DebugError("gdb caiu; reconecte")`. `health_check` já converte `DebugError`; assim a tool
  responde `error`+`hint` em vez de exceção. Alternativa: reintentar sozinho dentro do `_cmd`
  (arriscado: pode duplicar uma operação que já executou).
- **Logging do canal de controle no `ControlServer`.** Logar por requisição (`method`, `id`,
  duração, ok/erro) na thread de I/O do canal (nunca na EmuThread), com nível configurável e
  **desligado por padrão** para manter custo zero; sem corpo/payload.
- **Serializar o backend com um lock por backend.** Um `threading.Lock` (não reentrante basta)
  em torno de cada operação de `GdbBackend` (`_cmd`/connect/close) e de `UnixControlChannel`
  (`call`/`read_message`/reset), convertendo "chamadas concorrentes" em sequência no mesmo
  I/O. Rationale: o servidor é multi-thread (thread pool por chamada); o backend é um recurso
  serial (um gdb, um socket). Alternativa: serializar no `MCPServer` (não controlamos) ou um
  lock global (bloquearia gdb e canal entre si desnecessariamente). Atenção a deadlock:
  o `continue` em background usa `_run_thread`; o lock não deve ser mantido enquanto se espera
  o alvo parar (usar lock só nas escritas/leituras, ou um lock dedicado ao `_cmd`).

## Risks / Trade-offs

- [Parser de texto do gdb é frágil] → parsing tolerante (função `??`, linhas parciais) e
  testes unitários com saídas reais do gdb como fixture.
- [Thumb‑2 off-by-2 no `pc`] → verificar desassemblando o `pc` reportado (deve ser o `str` ao
  `DMAxCNT`); documentar a limitação.
- [Mapeamento `cpu` 0/1] → confirmar contra o `enum` do emulador e cobrir com teste.
- [Lista de breakpoints muda de formato entre versões do gdb] → parse por colunas tolerante e
  fixture da versão usada (`gdb-multiarch`).
- [Logging virar ruído/custo] → nível configurável, default `INFO`, sem payloads, canal de
  controle desligado por padrão e log fora da EmuThread.
- [Logar segredo/hex grande] → só metadados (nomes, tamanhos, durações, códigos de erro).

## Migration Plan

Mudança aditiva (o item de DMA ganha um campo; tools novas). Sem quebra das tools existentes.
Aplicar via `./deploy.sh up` (rebuilda emulador + imagem) e reiniciar o cliente.

## Open Questions

- `0x01ff9ff4` é região de código válida ou artefato do `R[15]`? Confirmar na implementação
  com o `pc` corrigido + `disassemble`.
