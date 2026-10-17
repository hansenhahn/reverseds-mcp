## Contexto

O MCP fala com dois backends (canal de controle e gdb). Ambos podem morrer/desconectar
(ex.: reinício do emulador), e o agente precisa de **diagnóstico rápido** e **erros claros**
em vez de timeouts genéricos. Snapshots úteis precisam sobreviver ao restart do MCP.

## Decisões

### Health-check

Tool `health_check()` que:
- chama `ping` no canal de controle;
- se o debugger estiver conectado, faz um read de teste (PC) — ou reporta "rodando" se
  houver `resume` ativo (`is_running`);
- devolve `{control, debug}` com `error`/`hint` por backend.

Não cria conexões novas nem derruba as existentes.

### Verificação no connect

Após `connect(core)`, ler o PC. Se falhar: `disconnect()` e retornar erro com hint para
reiniciar o emulador. Evita "conectou mas está morto".

### Snapshots persistentes

`mem_snapshot(name)` grava `snapshots/<name>.bin` (+ `.json` com `addr`/`size`) em
`RE_MCP_OUT_DIR`, além de manter em RAM. `state_diff(name)` usa a RAM; se ausente, carrega
do disco. Nome saneado com `basename` (sem path traversal).

### Contrato de erro

Helpers no `server.py`:
- `_error(exc, hint=None)` → `{"error", "hint"?}`.
- `_debug_error(exc)` → mapeia mensagens conhecidas para hints:
  - "alvo em execução" → use `debug_wait`/`debug_interrupt`;
  - "gdb não iniciado" → chame `debug_connect`.
- `_control(...)` adiciona hint quando o canal está indisponível.
- `screen_capture`: se o erro for timeout, hint "CPU haltada (use debug_resume) ou renderer
  não-software".

## Riscos

- Hints são heurísticos (por substring); manter mensagens estáveis no backend.
- Persistir snapshots não deve falhar a operação se o disco estiver cheio: reportar erro
  do snapshot, mas não corromper a RAM.
