## ADDED Requirements

### Requirement: Dados da ROM carregada

O canal de controle SHALL expor a ROM carregada no emulador. O método `rom.info` SHALL
devolver a identidade do cartucho (nome/caminho quando disponível, tamanho, gamecode e
checksum) e SHALL indicar `loaded: false` quando não houver cartucho. O método `rom.read`
SHALL devolver bytes da ROM carregada em um frame binário, validando os limites do cartucho.

#### Scenario: Identidade da ROM carregada
- **WHEN** o agente chama `rom.info` com um jogo carregado
- **THEN** recebe `loaded: true` com nome, tamanho, gamecode e checksum do cartucho

#### Scenario: Sem cartucho
- **WHEN** o agente chama `rom.info` sem cartucho carregado
- **THEN** recebe `loaded: false`, sem erro

#### Scenario: Ler bytes da ROM
- **WHEN** o agente chama `rom.read` com `offset` e `size` dentro da ROM carregada
- **THEN** recebe exatamente esses bytes em um frame binário

#### Scenario: Leitura fora dos limites
- **WHEN** o agente chama `rom.read` com um intervalo que ultrapassa o tamanho da ROM
- **THEN** o servidor responde com erro, sem encerrar a conexão

### Requirement: Carga mínima na thread de emulação (ROM)

A leitura da ROM pelo canal SHALL ocorrer na thread que atende o cliente, fora da thread de
emulação, e SHALL ser sob demanda. Nenhum trabalho adicional SHALL ser executado por quadro
por causa dos métodos de ROM.

#### Scenario: Leitura sob demanda
- **WHEN** nenhuma chamada `rom.read` está em andamento
- **THEN** a thread de emulação não executa trabalho adicional por causa dos métodos de ROM

#### Scenario: I/O fora da thread de emulação
- **WHEN** o agente lê um bloco da ROM
- **THEN** a cópia e o envio dos bytes ocorrem fora da thread de emulação
