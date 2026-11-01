## ADDED Requirements

### Requirement: Símbolos e aliases persistentes

O MCP SHALL permitir definir um símbolo/alias por endereço com nome, tipo, comentário e overlay
opcional, e SHALL persistir a tabela no diretório de saída para sobreviver ao restart. O MCP
SHALL permitir listar os símbolos e carregar um `.map` (`address name`), **mesclando** com os
aliases existentes por padrão.

#### Scenario: Definir e sobreviver ao restart
- **WHEN** o agente define `0x020A11C4 = desenha_painel` e o MCP reinicia
- **THEN** o símbolo continua disponível e resolve o mesmo endereço

#### Scenario: Carregar `.map` e mesclar
- **WHEN** o agente carrega um `.map` com símbolos do build e já existe um alias de RE
- **THEN** os dois coexistem na tabela (merge), sem apagar o alias

#### Scenario: Listar e consultar
- **WHEN** o agente lista os símbolos ou consulta um endereço
- **THEN** recebe nome, endereço, tipo, comentário e overlay quando houver

### Requirement: Anotação de hits e endereços

O MCP SHALL anotar com o símbolo resolvido os hits de `find_writer`/`find_reader`, os itens de
`hit_log_read` e o resultado de `addr_valid`.

#### Scenario: Hit anotado
- **WHEN** um watchpoint para em um PC coberto por um símbolo
- **THEN** o hit inclui o nome do símbolo (além do endereço)

#### Scenario: Endereço anotado
- **WHEN** o agente valida um endereço coberto por um símbolo
- **THEN** o resultado inclui o nome do símbolo

### Requirement: Snippets de decomp

O MCP SHALL permitir registrar e consultar um trecho de decomp (C + ASM comentado) por
endereço, persistindo os snippets no diretório de saída.

#### Scenario: Registrar snippet
- **WHEN** o agente registra C+ASM em um endereço
- **THEN** o snippet fica consultável pelo mesmo endereço em chamadas seguintes/restart

#### Scenario: Consultar snippet
- **WHEN** o agente consulta um endereço sem fornecer C/ASM
- **THEN** recebe o snippet existente ou um erro claro se não houver
