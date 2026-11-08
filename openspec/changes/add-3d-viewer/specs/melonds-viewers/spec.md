## ADDED Requirements

### Requirement: Janela de viewers com abas

O frontend SHALL oferecer uma janela de viewers com abas (`QTabWidget`), no estilo
do "VRAM Viewer" do No$gba, aberta por uma ação de menu habilitada apenas com jogo
carregado. A janela SHALL conter ao menos as abas OAM e 3D e SHALL ser o ponto de
entrada dos viewers.

#### Scenario: Abrir a janela de viewers
- **WHEN** o usuário abre a janela de viewers com um jogo carregado
- **THEN** a janela abre na aba OAM (padrão) com as abas OAM e 3D disponíveis

#### Scenario: Sem jogo
- **WHEN** não há jogo carregado
- **THEN** a ação fica desabilitada

### Requirement: Aba OAM preservada

O OAM viewer existente SHALL ser migrado para uma aba da janela de viewers,
preservando seleção, preview, detalhes e freeze. Fechar a janela SHALL parar o
refresh e não SHALL deixar a EmuThread pausada.

#### Scenario: Sem regressão no OAM
- **WHEN** o usuário usa a aba OAM
- **THEN** grid, preview, detalhes e freeze funcionam como antes

#### Scenario: Fechar a janela
- **WHEN** o usuário fecha a janela de viewers
- **THEN** o timer para e o jogo não fica pausado

### Requirement: Abrir o viewer 3D

O frontend SHALL oferecer um viewer 3D no padrão do viewer de OAM (ação de menu,
`openDlg`/`currentDlg`), habilitado apenas com jogo carregado. O viewer SHALL
renderizar o frame da camada 3D e uma lista de polígonos do frame.

#### Scenario: Abrir com jogo
- **WHEN** o usuário abre o viewer 3D com um jogo rodando
- **THEN** o diálogo mostra o frame 3D e a lista de polígonos

#### Scenario: Sem jogo
- **WHEN** não há jogo carregado
- **THEN** a ação fica desabilitada (como no viewer de OAM)

### Requirement: Overlay e seleção de polígonos

O viewer SHALL sobrepor os polígonos renderizados ao frame, com identificação
(`id`) e um destaque para o polígono selecionado. Selecionar na lista SHALL
destacar o polígono no overlay; selecionar o polígono SHALL mostrar seus vértices
com `screenpos (x/y/z/w)` e cor.

#### Scenario: Selecionar na lista
- **WHEN** o usuário seleciona um polígono na lista
- **THEN** o overlay destaca o polígono e os vértices aparecem com `screenpos`

#### Scenario: Localizar elemento
- **WHEN** o usuário procura um elemento visual
- **THEN** consegue identificar o polígono correspondente e sua posição de tela

### Requirement: Painel de estado 3D

O viewer SHALL exibir o estado 3D do frame: matrizes de
projeção/posição/vetor/textura/clip, viewport, fog/toon/edge, `GXStat` e níveis de
FIFO, coerentes com o `add-3d-inspection`. O viewer SHALL exibir o preview da
textura (`TexParam`/`TexPalette`) do polígono selecionado, reusando o decoder de
textura do inspection.

#### Scenario: Estado do frame
- **WHEN** o frame está congelado
- **THEN** o painel mostra matrizes/viewport/fog e níveis de FIFO daquele frame

#### Scenario: Preview de textura
- **WHEN** o usuário seleciona um polígono texturizado
- **THEN** o viewer mostra a textura correspondente

### Requirement: Freeze e refresh thread-safe

O viewer SHALL oferecer freeze/refresh no padrão do viewer de OAM: congelar SHALL
pausar a EmuThread e ler a lista de polígonos **finalizada no último VBlank**
(frame completo); o painel de estado SHALL refletir o ponto de pausa. Descongelar
SHALL retomar a emulação. O viewer NÃO SHALL escrever no core nem alterar o
comportamento de emulação.

#### Scenario: Congelar e descongelar
- **WHEN** o usuário congela e depois descongela
- **THEN** overlay e lista ficam estáveis (lista do último frame finalizado) e
  voltam a atualizar ao descongelar, sem afetar o jogo além da pausa
