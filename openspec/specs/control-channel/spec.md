# control-channel Specification

## Purpose
Define o canal de controle do emulador voltado ao agente (copiloto): como o
agente injeta input, lê a tela, salva/restaura estado, pausa a execução e recebe
eventos, de forma independente do canal de depuração GDB.

## Requirements

### Requirement: Servidor de controle dedicado

O sistema SHALL expor um servidor de controle em socket próprio, separado do
stub GDB. Por padrão SHALL usar um Unix domain socket; TCP SHALL ser opcional e
desabilitado por padrão.

#### Scenario: Servidor disponível em socket local
- **WHEN** o emulador é iniciado com o canal de controle habilitado
- **THEN** um Unix domain socket é criado e aceita conexões de clientes locais

#### Scenario: Independência do stub GDB
- **WHEN** um cliente de controle está conectado e um depurador GDB também está anexado
- **THEN** ambos operam simultaneamente sem que um derrube a conexão do outro

### Requirement: Protocolo e framing

O sistema SHALL trocar mensagens no formato JSON-RPC 2.0, com framing baseado em
`Content-Length: <N>\r\n\r\n` seguido do corpo JSON. Requisições, respostas,
erros e notificações SHALL seguir a semântica do JSON-RPC 2.0.

#### Scenario: Chamada de método bem-sucedida
- **WHEN** o cliente envia uma requisição JSON-RPC válida com um método conhecido
- **THEN** o servidor responde com `result` e o `id` correspondente

#### Scenario: Método desconhecido
- **WHEN** o cliente envia uma requisição com um método não suportado
- **THEN** o servidor responde com um erro JSON-RPC de método não encontrado

#### Scenario: Frame malformado
- **WHEN** o cliente envia um header sem `Content-Length` válido
- **THEN** o servidor responde com erro de protocolo e não encerra a conexão por isso

### Requirement: Frame binário para payloads grandes

O sistema SHALL suportar um frame binário dedicado, distinto das mensagens JSON,
para transferir payloads grandes (por exemplo, o framebuffer) sem codificação
base64. O frame binário SHALL ter um cabeçalho com tamanho e tipo antes dos bytes
crus.

#### Scenario: Captura de tela via frame binário
- **WHEN** o cliente solicita uma captura de tela
- **THEN** o servidor envia os bytes do framebuffer em um frame binário, sem base64

### Requirement: Injeção de input — teclas

O sistema SHALL permitir ao agente definir o estado das teclas via o método
`input.key`, usando uma máscara **active-low** no mesmo layout do `KEYINPUT`
(1 = solto, 0 = pressionado). O input do agente SHALL ser combinado (AND) com o
input do host, de modo que humano e agente operem a mesma instância
simultaneamente.

#### Scenario: Pressionar um botão
- **WHEN** o agente envia `input.key` com o bit do botão A zerado
- **THEN** o `KEYINPUT` observado no emulador passa a indicar A pressionado

#### Scenario: Merge com o host
- **WHEN** o humano segura o botão B e o agente injeta o botão A
- **THEN** o emulador registra A e B pressionados ao mesmo tempo

#### Scenario: Soltar tudo
- **WHEN** o agente envia `input.release`
- **THEN** nenhuma tecla permanece injetada pelo agente

### Requirement: Injeção de input — tela de toque

O sistema SHALL permitir ao agente pressionar a tela de toque em coordenadas
`(x, y)` via `input.touch`, e soltá-la via `input.release`. O estado de toque
injetado SHALL persistir até ser alterado.

#### Scenario: Pressionar a tela
- **WHEN** o agente envia `input.touch` com coordenadas válidas
- **THEN** o emulador registra a caneta pressionada nessas coordenadas

#### Scenario: Soltar a tela
- **WHEN** o agente envia `input.release`
- **THEN** o emulador registra a caneta solta

### Requirement: Captura de tela parametrizável

O sistema SHALL expor `screen.capture` para uma captura pontual e um modo de
streaming, ambos parametrizáveis. Os parâmetros SHALL incluir: telas (superior,
inferior ou ambas), formato de pixel e, no streaming, intervalo e duração (ou
número de amostras). A captura SHALL refletir o quadro mais recente disponível e
SHALL retornar a imagem **composta** (mistura de todas as camadas e do 3D) em cor
plena, com 8 bits por canal — e não uma paleta de 256 cores.

#### Scenario: Captura pontual das duas telas
- **WHEN** o agente chama `screen.capture` pedindo as duas telas
- **THEN** o servidor retorna os pixels compostos das telas superior e inferior com suas dimensões

#### Scenario: Captura com formato escolhido
- **WHEN** o agente pede o formato RGBA8888
- **THEN** os bytes retornados estão em RGBA8888, 8 bits por canal

#### Scenario: Streaming com intervalo e duração
- **WHEN** o agente pede captura a cada 1000 ms por 10000 ms
- **THEN** o servidor entrega uma amostra por segundo durante dez segundos, sem capturar os quadros intermediários

#### Scenario: Streaming por número de amostras
- **WHEN** o agente pede 10 amostras a cada 1000 ms
- **THEN** o servidor entrega exatamente dez amostras e encerra o streaming

#### Scenario: Cor plena na imagem composta
- **WHEN** a cena composta usa mais cores do que uma única paleta de 256
- **THEN** a imagem retornada preserva todas as cores (8 bits por canal), sem quantização para 256

### Requirement: Savestate

O sistema SHALL permitir `savestate.save` e `savestate.load` em um slot
identificado. A operação SHALL preservar/restaurar o estado completo da emulação
(CPU, memória e periféricos).

#### Scenario: Salvar e restaurar
- **WHEN** o agente salva em um slot e depois carrega o mesmo slot
- **THEN** o estado da emulação volta ao ponto salvo

### Requirement: Controle de execução

O sistema SHALL permitir pausar e retomar a execução via `emu.pause` e
`emu.resume`, sem desconectar os clientes.

#### Scenario: Pausar e retomar
- **WHEN** o agente chama `emu.pause` e depois `emu.resume`
- **THEN** a emulação para de avançar e depois volta a avançar

### Requirement: Thread-safety das operações de núcleo

Operações que alteram o estado do núcleo (input, savestate, pause) SHALL ser
executadas na thread de emulação, e não na thread que atende o socket.

#### Scenario: Savestate durante execução
- **WHEN** o agente solicita `savestate.save` com a emulação rodando
- **THEN** a operação é aplicada de forma consistente, sem corromper o estado

### Requirement: Carga mínima na thread de emulação

A thread de emulação SHALL sofrer o mínimo possível de carga adicional. Ela NÃO
SHALL realizar I/O de socket, serialização JSON, nem logging do tráfego de
controle. O trabalho adicionado por quadro SHALL ser O(1) e SHALL NOT alocar
memória. Sem cliente conectado/assinante, o custo adicional SHALL ser
desprezível.

#### Scenario: I/O e serialização fora da thread de emulação
- **WHEN** o agente envia requisições e recebe respostas ou eventos
- **THEN** toda a leitura/escrita do socket e a codificação JSON ocorrem fora da thread de emulação

#### Scenario: Trabalho por quadro sem alocação
- **WHEN** a emulação roda com o canal de controle ativo
- **THEN** o trabalho adicionado por quadro é O(1) e não faz alocação de memória

#### Scenario: Eventos sinalizados, não codificados na thread de emulação
- **WHEN** um quadro é produzido e há um assinante
- **THEN** a thread de emulação apenas sinaliza o evento, e a codificação e o envio acontecem em outra thread

#### Scenario: Sem cliente, sem custo por quadro
- **WHEN** nenhum cliente de controle está conectado ou assinando eventos
- **THEN** a thread de emulação não executa trabalho adicional por quadro

#### Scenario: Captura sob demanda
- **WHEN** o agente não solicitou captura de tela
- **THEN** a thread de emulação não copia o framebuffer

### Requirement: Controle responsivo com o debugger anexado

Enquanto o stub GDB tem o alvo **parado**, o canal de controle SHALL permanecer
responsivo: as operações de controle (captura, savestate, input, frame-step) SHALL ser
atendidas, sem exigir que o agente desconecte o debugger.

#### Scenario: Capturar com o debugger parado
- **WHEN** o gdb está anexado e o alvo haltado, e o agente pede uma captura
- **THEN** a captura retorna o framebuffer atual, sem expirar

#### Scenario: Savestate com o debugger parado
- **WHEN** o alvo está haltado pelo gdb e o agente salva o estado
- **THEN** o savestate é gravado

#### Scenario: Frame-step com o debugger anexado
- **WHEN** o gdb está anexado e o agente pede para avançar quadros
- **THEN** a operação é atendida (não expira)

### Requirement: A emulação não avança com a CPU parada

Enquanto o depurador mantém o alvo parado, a emulação NÃO SHALL avançar quadros; o laço
SHALL apenas atender o canal de controle.

#### Scenario: CPU parada não avança
- **WHEN** o depurador mantém o alvo parado
- **THEN** nenhum quadro é emulado até o agente retomar (via gdb ou `emu.resume`)
