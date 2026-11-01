## ADDED Requirements

### Requirement: Captura e checagem de argumentos

O MCP SHALL oferecer `args_on_hit(addr, condition, count, timeout, stack_words, schema)` que
arma um breakpoint, captura `r0..r3`, `sp`, `lr`, `cpsr` e palavras da pilha em cada hit e
compara com o schema fornecido, reportando por argumento o esperado, o obtido e `ok`. O
breakpoint SHALL ser removido ao final, mesmo em erro/timeout.

#### Scenario: Capturar argumentos
- **WHEN** o agente chama `args_on_hit` em um callsite alcançável
- **THEN** recebe os registradores e a pilha do(s) hit(s)

#### Scenario: Schema válido
- **WHEN** o schema espera `r0=2` e `r1` ponteiro e o hit corresponde
- **THEN** todos os checks vêm `ok=true`

#### Scenario: Divergência
- **WHEN** o schema espera um ponteiro em `r1` e o runtime manda `0x9`
- **THEN** o check de `r1` vem `ok=false` com esperado/obtido

#### Scenario: Timeout
- **WHEN** o callsite não é atingido no tempo
- **THEN** o MCP retorna uma lista vazia e remove o breakpoint

### Requirement: Xref de campo em runtime

O MCP SHALL oferecer `field_xref(base, offset, kind)` e `field_writers(base, offset)` que
observam `base+offset` com watchpoint de leitura/escrita e devolvem o PC (e símbolo) do
acesso, ou `hit=null` se não ocorrer no tempo. `base` SHALL aceitar endereço ou nome de
símbolo.

#### Scenario: Writer do campo
- **WHEN** o agente pede os writers de `base+off` e há uma escrita
- **THEN** recebe o PC do escritor e o símbolo quando houver

#### Scenario: Sem acesso
- **WHEN** nenhum acesso ocorre no tempo
- **THEN** o resultado é `hit=null`

#### Scenario: Base por símbolo
- **WHEN** `base` é o nome de um símbolo
- **THEN** o endereço do símbolo é usado

### Requirement: Candidato de struct a partir do código

O MCP SHALL oferecer `struct_candidate(code, size, mode)` que desmonta uma faixa de código,
coleta acessos `[rN, #imm]` de loads/stores (exceto `sp`/`pc`), agrupa por offset com a
largura máxima e o conjunto de registradores, e devolve os campos e um esqueleto C com
padding. O resultado SHALL ser explicitamente um **candidato** (over-aproximado).

#### Scenario: Campos observados
- **WHEN** o código tem `ldr/ldrb/strh` com offsets
- **THEN** o resultado lista os offsets, larguras e registradores usados

#### Scenario: Esqueleto C
- **WHEN** há campos em offsets não contíguos
- **THEN** o C gerado inclui padding entre eles
