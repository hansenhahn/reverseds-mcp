## ADDED Requirements

### Requirement: Breakpoints condicionais e comandos no hit

O MCP SHALL permitir criar um breakpoint de código com uma **condição** opcional (expressão
gdb por registrador/memória) e uma lista opcional de **comandos** executados no hit. O
resultado SHALL incluir o número e o endereço do breakpoint. Se a condição ou os comandos
falharem, o MCP SHALL remover o breakpoint recém-criado e retornar `error` + `hint`, sem
deixar configuração parcial.

#### Scenario: Condição por registrador
- **WHEN** o agente cria um breakpoint em um endereço com `condition="$r3 == 0x30"`
- **THEN** a execução só para quando a condição for verdadeira

#### Scenario: Condição por memória
- **WHEN** o agente cria um breakpoint com uma condição que lê a memória
  (ex.: `*(unsigned short*)0x0600F448 != 0`)
- **THEN** o gdb avalia a condição e só reporta a parada quando ela for verdadeira

#### Scenario: Auto-patch no hit
- **WHEN** o agente cria um breakpoint com `commands` que escrevem um imediato e mandam
  continuar (ex.: `set {unsigned int}0xADDR = 0xVALUE` + `continue`)
- **THEN** a escrita acontece no hit e a execução continua, sem o loop manual
  `resume → wait → mem_write`

#### Scenario: Comando inválido
- **WHEN** a condição ou um dos comandos é inválido para o gdb
- **THEN** o MCP remove o breakpoint criado e retorna `error` + `hint`

#### Scenario: Breakpoint simples
- **WHEN** o agente cria um breakpoint sem condição e sem comandos
- **THEN** o comportamento é o mesmo de antes (para ao atingir o endereço)

### Requirement: Backtrace com fallback de pilha

`debug_backtrace` SHALL retornar os frames do gdb e, quando o gdb devolver menos de 4 frames,
SHALL completar a pilha varrendo `sp..sp+0x800` por **return addresses** em ITCM, RAM
principal ou ARM9 BIOS, com alinhamento de 2 bytes (ARM/Thumb) e confirmação de que os bytes
anteriores formam um `bl`/`blx` que retorna ao candidato. O MCP SHALL excluir o PC atual e
frames já conhecidos, deduplicar, limitar a quantidade de candidatos e marcar cada frame com
sua origem (`source="gdb"` ou `source="stack"`). Se a pilha não puder ser lida, SHALL retornar
apenas os frames do gdb.

#### Scenario: `bt` curto
- **WHEN** o gdb devolve 2 frames e a pilha contém return addresses válidos
- **THEN** o resultado contém os frames do gdb seguidos dos candidatos, cada um com
  `source="stack"`

#### Scenario: `bt` suficiente
- **WHEN** o gdb devolve 4 ou mais frames
- **THEN** o MCP não varre a pilha e devolve apenas frames com `source="gdb"`

#### Scenario: Candidato sem chamada
- **WHEN** um valor da pilha cai em região de código mas não é precedido por `bl`/`blx`
- **THEN** ele não é retornado como frame

#### Scenario: Duplicados e PC atual
- **WHEN** um candidato da pilha repete o PC atual ou um frame já retornado pelo gdb
- **THEN** ele é omitido do resultado

#### Scenario: Pilha ilegível
- **WHEN** a leitura da pilha falha (ex.: `sp` inválido)
- **THEN** o MCP retorna os frames do gdb, sem erro
