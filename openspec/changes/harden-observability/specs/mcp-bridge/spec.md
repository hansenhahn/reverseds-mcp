## ADDED Requirements

### Requirement: Logging estruturado do MCP

O MCP SHALL emitir logs estruturados para `stderr` (capturáveis por `deploy.sh logs`), com
nível configurável por `RE_MCP_LOG_LEVEL` (default `INFO`). Os logs SHALL cobrir: início e
configuração (sem segredos), conexão/reconexão do canal de controle, ciclo de vida do gdb
(conectar/desconectar/queda), cada chamada de tool (nome, duração e ok/erro) e erros com
contexto. O log NÃO SHALL expor segredos nem payloads grandes (ex.: framebuffer); com nível
`OFF`/`ERROR`, o volume SHALL ser mínimo.

#### Scenario: Chamada de tool logada
- **WHEN** o agente chama uma tool
- **THEN** há uma linha de log com o nome da tool, a duração e se terminou ok ou em erro

#### Scenario: Erro com contexto
- **WHEN** uma tool falha (ex.: canal indisponível, gdb caído)
- **THEN** o log registra o erro com contexto suficiente para diagnosticar (backend, operação)

#### Scenario: Nível configurável
- **WHEN** `RE_MCP_LOG_LEVEL` é ajustado (ex.: `DEBUG`, `ERROR`, `OFF`)
- **THEN** o volume de logs muda de acordo, sem alterar o comportamento das tools

### Requirement: Backend morto não derruba a tool

Quando o gdb (ou o canal de controle) morre no meio de uma operação, a tool SHALL retornar o
contrato `{"error", "hint"}` (ex.: reconectar) em vez de deixar a exceção escapar. O backend
SHALL marcar-se como desconectado e a próxima chamada SHALL reconectar em vez de reusar o
processo morto.

#### Scenario: `health_check` com gdb morto
- **WHEN** o gdb caiu (pipe quebrado) e o agente chama `health_check`
- **THEN** o campo `debug` traz `error` e `hint`, e a tool não estoura exceção

#### Scenario: Comando com gdb caído
- **WHEN** o agente usa uma tool de debug com o gdb caído
- **THEN** a tool responde `error` + `hint` e a próxima chamada reconecta

### Requirement: Acesso serializado ao backend

O MCP SHALL serializar o acesso a cada backend (gdb e canal de controle) com um lock, de modo
que chamadas de tool **concorrentes** (as tools síncronas rodam em thread pool) nunca
intercalem escrita/leitura no mesmo processo/socket. Requisições concorrentes SHALL ser
atendidas em sequência, sem misturar respostas, prompt ou reenviar comandos.

#### Scenario: Leituras paralelas de registradores
- **WHEN** o agente lê vários registradores em paralelo (chamadas concorrentes)
- **THEN** todas retornam o valor correto do registrador pedido, sem misturar respostas nem
  quebrar a sessão do gdb

#### Scenario: Chamadas paralelas no canal de controle
- **WHEN** duas chamadas de canal correm em paralelo
- **THEN** cada uma recebe a sua resposta (casa por `id`), sem consumir a resposta da outra

