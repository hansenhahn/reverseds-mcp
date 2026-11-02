## ADDED Requirements

### Requirement: Checagem de contrato no runtime

O MCP SHALL oferecer `contract_check(addr, schema, ret_schema=None, condition=None, count=1,
timeout=30, stack_words=8)` que capture os argumentos no callsite, compare com `schema` e,
quando `ret_schema` for fornecido, capture o primeiro retorno e compare com `ret_schema`. O
resultado SHALL incluir `ok`, `hits` e `divergences` (por argumento/retorno, com esperado,
obtido e `checked`). Breakpoints temporários SHALL ser removidos mesmo em erro/timeout.

#### Scenario: Argumentos válidos
- **WHEN** o schema espera `r0=2` e `r1` ponteiro e o hit corresponde
- **THEN** todos os checks vêm `ok=true` e `divergences` vazio

#### Scenario: Divergência de argumento
- **WHEN** o schema espera um ponteiro em `r1` e o runtime manda `0x9`
- **THEN** a divergência de `r1` vem com esperado/obtido

#### Scenario: Retorno válido
- **WHEN** `ret_schema` espera `r0=0` e a função retorna 0
- **THEN** o check de retorno vem `ok=true`

#### Scenario: Sem retorno
- **WHEN** a função não retorna ao `lr` no timeout
- **THEN** o hit vem com `return=null` e o contrato `ok=false`

### Requirement: Diff de patch ASM × C

O MCP SHALL oferecer `diff_patch(asm_patch, c_equiv)` que recebe listas de escritas
`{addr, bytes}` (patch ASM e o equivalente compilado do C), lê a memória atual nas faixas
tocadas, aplica os dois patches sobre uma cópia e devolve `iguais`, `count`, `diffs` e
`regions`. `diffs` SHALL listar cada byte divergente com `addr`, `asm` e `c`.

#### Scenario: Patches equivalentes
- **WHEN** as duas listas escrevem os mesmos bytes nos mesmos endereços
- **THEN** `iguais=true` e `diffs=[]`

#### Scenario: Patches divergentes
- **WHEN** um byte difere (ou só um lado escreve um endereço)
- **THEN** `iguais=false` e `diffs` lista o endereço com os dois valores

#### Scenario: Escrita sobreposta
- **WHEN** há escritas sobrepostas no mesmo patch
- **THEN** prevalece a última escrita e a comparação usa o efeito final

#### Scenario: Entrada inválida
- **WHEN** um spec não tem `addr`/`bytes`, o hex é inválido ou passa do limite
- **THEN** a tool retorna erro sem escrever memória
