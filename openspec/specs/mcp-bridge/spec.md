# mcp-bridge Specification

## Purpose

Conecta o servidor MCP aos dois canais do melonDS (canal de controle e stub GDB),
cuidando de configuração, escolha de core e erros — sem tocar no emulador.

## Requirements

### Requirement: Conexão ao canal de controle

O servidor MCP SHALL conectar ao canal de controle do melonDS por socket Unix,
com o caminho configurável, e SHALL reportar erro claro quando o emulador não
estiver disponível.

#### Scenario: Conectar
- **WHEN** o MCP inicia com o caminho do socket configurado
- **THEN** ele consegue chamar `ping` e recebe `{"pong": true}`

#### Scenario: Emulador ausente
- **WHEN** o socket não existe ou não conecta
- **THEN** o MCP reporta um erro claro (sem travar) e permite reconfigurar

### Requirement: Conexão ao gdb (stub GDB)

O servidor MCP SHALL gerenciar um `gdb` (`gdb-multiarch`, com pwndbg) conectado ao
stub GDB (RSP) do core escolhido (ARM9 ou ARM7), com o limite de watchpoint de
hardware aplicado.

#### Scenario: Escolher o core
- **WHEN** o agente pede para depurar o ARM9
- **THEN** o MCP conecta o gdb na porta do ARM9 e passa a operar nesse core

#### Scenario: Watchpoint de hardware garantido
- **WHEN** o gdb é conectado
- **THEN** o limite de watchpoint de hardware é aplicado, de modo que os watchpoints usem hardware

### Requirement: Exposição e descoberta de tools

O servidor MCP SHALL expor as tools das capabilities de controle, depuração e RE,
e SHALL permitir ao agente descobri-las.

#### Scenario: Descoberta de tools
- **WHEN** o agente lista as tools do MCP
- **THEN** aparecem as tools de emulação, depuração e RE

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
