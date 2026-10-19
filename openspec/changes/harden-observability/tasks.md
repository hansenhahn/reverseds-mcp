## 1. Captura vazia é erro

- [ ] 1.1 Em `screen_capture`, quando `save_framebuffer_pngs` devolve `paths == []`, retornar `error` + `hint` (captura veio vazia; conferir CPU parada/renderer). Verificar: teste unitário com payload vazio → `error` + `hint`, sem sucesso vazio; `pytest` verde.
- [ ] 1.2 Cobrir o caminho feliz no mesmo teste (payload com 1 frame → `paths` com 1 arquivo), garantindo que o erro só aparece quando não há frame.

## 2. DMA: `cpu` e `pc` da instrução

- [ ] 2.1 `DmaTransfer`: adicionar `cpu: int` e `from_raw(cpu, ch, src, dst, cnt, pc)`; `DmaTrace.collect` passa `raw["cpu"]`; `_dma_dict` expõe `"cpu": "arm9"`/`"arm7"` (0→arm9, 1→arm7). Verificar: teste unitário de decode/serialização com `cpu` 0 e 1.
- [ ] 2.2 Emulador: em `DMA::WriteCnt`, registrar o endereço da instrução do store (`R[15] - ((CPSR & 0x20) ? 2 : 4)`) em vez do `R[15]` cru. Verificar: com um savestate, o `pc` do DMA desassembla como o `str` que escreve `DMAxCNT` (não o endereço seguinte); registrar a limitação de Thumb‑2 na doc.
- [ ] 2.3 Resolver a Open Question do `0x01ff9ff4`: confirmar via `disassemble` do `pc` corrigido se é código válido; se não, documentar a causa (região/artefato) antes de fechar a tarefa.

## 3. Backtrace e lista de breakpoints

- [ ] 3.1 Porta `Debugger` + domínio: tipos `StackFrame` (índice, `pc`, `function`) e `Breakpoint` (`number`, `type`, `address`, `condition`, `enabled`); métodos `backtrace()` e `breakpoints()`. Verificar: `pyright` verde e fakes de teste satisfazendo a porta.
- [ ] 3.2 `GdbBackend`: parsear `bt` e `info breakpoints` de forma tolerante (`??`, linhas parciais). Verificar: testes unitários com fixtures de saída real do `gdb-multiarch` (vazio, `??`, watchpoint com condição).
- [ ] 3.3 Tools `debug_backtrace()` e `list_breakpoints()` no estilo existente (erro claro com alvo rodando; lista vazia sem erro). Verificar: teste unitário com `Debugger` fake; smoke no emulador com alvo parado.

## 4. Logging e "backend morto"

- [ ] 4.1 MCP: logger `re_mcp` para `stderr` com nível `RE_MCP_LOG_LEVEL` (default `INFO`) e wrapper nas tools logando nome, duração e ok/erro (sem payload). Verificar: rodar uma tool e ver a linha em `./deploy.sh logs`; mudar o nível e ver o volume mudar.
- [ ] 4.2 MCP: logar conexão/reconexão do canal e ciclo do gdb (connect/disconnect/queda). Verificar: conectar e desconectar o gdb e ver os eventos no log.
- [ ] 4.3 MCP: em `GdbBackend`, capturar `BrokenPipeError`/`OSError` (escrita/leitura), marcar desconectado e levantar `DebugError`; `health_check` e demais tools retornam `error` + `hint`. Verificar: matar o gdb e chamar `health_check` → `debug` com `error`+`hint`, sem exceção; a chamada seguinte reconecta.
- [ ] 4.4 Emulador: logging do canal no `ControlServer` (método, `id`, duração, ok/erro; conexão/desconexão), nível configurável, **desligado por padrão**, fora da EmuThread e sem payload. Verificar: com o log ligado, as linhas aparecem; desligado, não emite; build compila.
- [ ] 4.5 Testes unitários: formatação/nível do logger e conversão de `BrokenPipeError` em `DebugError` (fake de gdb).
- [ ] 4.6 Serializar o backend do gdb (lock em `_cmd`/connect/close) e o do canal (`call`/`read_message`/reset). Verificar: teste com N threads chamando `read_register` em paralelo sobre um gdb fake que casa comando↔resposta → cada uma recebe o valor certo, sem misturar nem quebrar.
- [ ] 4.7 Smoke: caso com várias `debug_read_register` **em paralelo** contra o gdb real → todas ok e o gdb segue vivo. Verificar: caso passa e o backend continua respondendo.

## 5. Validação

- [ ] 5.1 `uv run python -m pytest`, `uv run pyright` e `uv run lint-imports` verdes. Verificar: saída dos três comandos sem erros.
- [ ] 5.2 Build do emulador (`./deploy.sh up` ou `cmake --build`) sem regressão e `./smoke/run-smoke.sh "<rom>"` verde. Verificar: suíte 8/8 e o caso novo de DMA (se adicionado) passando.
- [ ] 5.3 `openspec validate harden-observability --strict` OK.
