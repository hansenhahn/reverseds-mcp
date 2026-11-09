## ADDED Requirements

### Requirement: Override de conteúdo do cartucho por range

O sistema SHALL permitir registrar um override que serve os bytes de um arquivo do host para
um range absoluto `[start, end)` da ROM. Toda leitura de dados do cartucho cujo offset caia no
range SHALL ser servida a partir do arquivo do host no offset correspondente (`addr - start`),
tanto para leituras de CPU quanto para transferências por DMA. Uma leitura sem override
registrado NÃO SHALL mudar o comportamento de emulação.

#### Scenario: Override no-op
- **WHEN** o agente registra como override uma cópia idêntica do arquivo original
- **THEN** o jogo continua com o mesmo comportamento e o contador de leituras servidas é maior que zero

#### Scenario: Mudança visível
- **WHEN** o agente registra um arquivo do host com um byte alterado dentro do range
- **THEN** o jogo lê o byte alterado na próxima carga do arquivo

#### Scenario: Leitura via DMA
- **WHEN** o jogo carrega o arquivo por transferência DMA do cartucho
- **THEN** os bytes servidos vêm do override, não da imagem original da ROM

#### Scenario: Sem override ativo
- **WHEN** nenhum override está registrado
- **THEN** as leituras do cartucho continuam vindo da ROM original, sem custo de comportamento

#### Scenario: Palavra cruzando o limite do range
- **WHEN** uma palavra de 4 bytes começa dentro e termina fora do range
- **THEN** a parte dentro vem do override e a parte fora vem da ROM original

### Requirement: Semântica de tamanho do override

O range válido SHALL ser determinado pelos offsets `start`/`end` recebidos. Se o arquivo do
host for menor que o range, os bytes ausentes SHALL ser zero (zero-fill). Se for maior, os
bytes além de `end` SHALL ser ignorados.

#### Scenario: Arquivo do host menor
- **WHEN** o arquivo do host tem menos bytes que `end - start`
- **THEN** as leituras acima do tamanho do host retornam zero

#### Scenario: Arquivo do host maior
- **WHEN** o arquivo do host tem mais bytes que `end - start`
- **THEN** somente os primeiros `end - start` bytes são servidos e o excedente é ignorado

### Requirement: Ciclo de vida dos overrides

Os overrides SHALL existir apenas enquanto o cartucho carregado existir: ao trocar ou ejetar o
cartucho, os overrides SHALL ser descartados. Overrides NÃO SHALL ser gravados em savestate nem
restaurados ao carregar um savestate.

#### Scenario: Troca de cartucho
- **WHEN** outro cartucho é carregado no emulador
- **THEN** não há overrides ativos para o novo cartucho

#### Scenario: Carregar savestate
- **WHEN** o agente carrega um savestate com overrides ativos
- **THEN** os overrides continuam ativos (não fazem parte do savestate)

### Requirement: Hot reload do conteúdo

O sistema SHALL permitir recarregar o arquivo do host sem reiniciar o emulador, publicando o
novo conteúdo de forma atômica. Durante a troca, uma leitura concorrente SHALL ver o buffer
antigo ou o novo, nunca um buffer parcial.

#### Scenario: Recarregar após editar o host
- **WHEN** o agente altera o arquivo do host e chama o reload
- **THEN** as leituras seguintes usam o novo conteúdo

#### Scenario: Reload concorrente com leitura
- **WHEN** o reload acontece enquanto o jogo lê o range
- **THEN** nenhuma leitura retorna bytes de um buffer parcialmente preenchido
