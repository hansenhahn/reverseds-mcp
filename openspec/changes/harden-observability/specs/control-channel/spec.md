## ADDED Requirements

### Requirement: Logging do canal de controle

O canal de controle SHALL registrar, de forma estruturada e com nível configurável (default
sem custo quando desligado), cada requisição e erro: o método, o `id`, a duração e o resultado
(ok/erro, com código), além de conexão e desconexão de clientes. O logging SHALL ocorrer
**fora** da thread de emulação e NÃO SHALL incluir payloads grandes (ex.: framebuffer) nem
segredos. Com o logging desligado, o custo adicional SHALL ser desprezível.

#### Scenario: Requisição logada
- **WHEN** o cliente envia uma requisição e o servidor responde
- **THEN** há uma linha de log com o método, o `id`, a duração e o resultado

#### Scenario: Erro logado
- **WHEN** uma requisição falha (método desconhecido, frame malformado, erro interno)
- **THEN** o log registra o método e o código de erro

#### Scenario: Conexão e desconexão
- **WHEN** um cliente conecta ou desconecta
- **THEN** o log registra o evento

#### Scenario: Logging desligado
- **WHEN** o logging está desligado
- **THEN** o canal não emite linhas de log e o custo por requisição permanece desprezível
