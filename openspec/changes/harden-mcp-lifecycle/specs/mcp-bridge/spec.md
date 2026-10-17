## Purpose

Reforça o ciclo de vida e o diagnóstico dos backends (canal de controle + gdb): health-check,
verificação de conexão, snapshots persistentes e um contrato de erro único com dicas.

## ADDED Requirements

### Requirement: Health-check

O MCP SHALL oferecer `health_check()` que reporte o estado do **canal de controle** e do
**debugger** (conectado/rodando), com `error`/`hint` por backend quando houver falha, sem
criar nem derrubar conexões.

#### Scenario: Emulador e debugger ok
- **WHEN** o canal responde ao `ping` e o debugger está conectado e parado
- **THEN** o resultado reporta ambos ok (e o PC)

#### Scenario: Canal indisponível
- **WHEN** o socket do canal de controle não responde
- **THEN** o campo `control` traz `error` e um `hint`

### Requirement: Verificação de conexão

Ao conectar o debugger, o MCP SHALL fazer uma leitura de teste; se falhar, SHALL
desconectar e reportar erro com hint (stub possivelmente travado).

#### Scenario: Stub morto
- **WHEN** o `connect` sucede mas a leitura de teste falha
- **THEN** o MCP desconecta e retorna `error` + `hint`

### Requirement: Snapshots persistentes

`mem_snapshot` SHALL persistir a captura em disco (`RE_MCP_OUT_DIR/snapshots`) além de
mantê-la em RAM. `state_diff` SHALL carregar do disco quando a captura não estiver em RAM.

#### Scenario: Snapshot sobrevive ao restart
- **WHEN** um snapshot foi gravado e o MCP reinicia
- **THEN** `state_diff` ainda consegue comparar usando o arquivo em disco

#### Scenario: Nome do snapshot
- **WHEN** o agente informa um `name`
- **THEN** o arquivo é criado com o nome saneado (sem path traversal)

### Requirement: Contrato de erro único

As tools SHALL retornar erros no formato `{"error": <msg>, "hint"?: <dica>}`, com dicas para
os casos comuns (alvo em execução, gdb não iniciado, canal indisponível).

#### Scenario: Comando com alvo rodando
- **WHEN** uma tool de debug é usada com o alvo em execução
- **THEN** o erro traz hint para usar `debug_wait`/`debug_interrupt`
