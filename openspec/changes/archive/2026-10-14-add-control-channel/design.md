## Context

O melonDS roda o núcleo numa única thread de emulação (`EmuThread`); a GUI (Qt)
comunica-se com ela por uma fila de mensagens. O input do host é aplicado por
frame em `EmuThread`, via `NDS::SetKeyMask` / `NDS::TouchScreen`. Já existe o
stub GDB (canal de debug, conexão única) e, no fork, input via `qRcmd`
(`monitor key/touch/release`). Ver `proposal.md` para a motivação.

## Goals / Non-Goals

**Goals:**
- Um canal de controle local, independente do GDB, capaz de: input, captura de
  tela, savestate, pause/resume e eventos.
- Protocolo simples, testável e implementável nos dois lados (C++ no melonDS,
  Python no MCP).
- Não regredir performance nem alterar o comportamento de emulação.

**Non-Goals:**
- Substituir o canal de debug: leitura/**dump de memória bruta**, breakpoints e watchpoints continuam no GDB (RSP). O `screen.capture` retorna a imagem composta (memória de host), não bytes de endereços emulados — sem sobreposição com dump de memória.
- Expor controle pela rede por padrão.
- Autenticação/criptografia nesta versão (é socket local).
- Emular múltiplas instâncias por um único servidor.

## Decisions

### D1. JSON-RPC 2.0 em vez de MessagePack-RPC
**Decisão**: usar JSON-RPC 2.0.
**Por quê**: canal de baixa frequência e local — legibilidade do tráfego (dá pra
inspecionar com `nc`) e ubiquidade pesam mais que compactação; o único payload
grande (framebuffer) é resolvido por frame binário (D3), então a vantagem de
binário nativo do msgpack deixa de ser decisiva.
**Alternativas**: MessagePack-RPC (estilo Neovim) — mais compacto, binário e
eventos nativos, mas wire opaco e mais glue; fica como troca localizada se o
overhead incomodar. gRPC/ZeroMQ — descartados por peso e complexidade.

### D2. Framing `Content-Length` (estilo LSP/DAP) para JSON
**Decisão**: mensagens JSON trafegam como `Content-Length: <N>\r\n\r\n<body>`.
**Por quê**: framing textual comprovado, trivial de parsear em C++ e Python, e
independente de delimitadores dentro do JSON.
**Alternativas**: newline-delimited JSON (simples, mas frágil com strings
multilinha) e envelope binário uniforme (mais compacto, porém ilegível).

### D3. Frame binário dedicado para payloads grandes
**Decisão**: quando uma resposta carrega binário grande, o JSON-RPC anuncia o
tamanho (ex.: `screen.capture` → `result.binary.bytes = N`) e o servidor emite
em seguida um frame cru `[u32 BE N][bytes]`, lido exatamente por N bytes.
**Por quê**: evita base64 (33% de overhead) e mantém o JSON legível para o resto.
**Alternativas**: base64 no JSON (mais simples, mais lento/volumoso) — aceitável
como fallback inicial.

### D4. Transporte: Unix domain socket por padrão, TCP opt-in
**Decisão**: `--control-socket <path>` (Unix domain) por padrão; TCP só se
habilitado.
**Por quê**: local, sem porta a conflitar, controle de acesso por permissão de
arquivo, e mais rápido. TCP quando se quiser controlar de outra máquina.

### D5. Threading: thread de socket + fila para a EmuThread
**Decisão**: uma thread dedicada aceita/lerá o socket e enfileira requisições;
toda operação que toca o núcleo é executada na EmuThread (reusando a fila de
mensagens existente). Input usa os campos compartilhados já adicionados
(`AgentInputMask`/`AgentTouching`), que a EmuThread lê por frame.
**Por quê**: o núcleo é single-thread; mexer nele fora da EmuThread é race.
**Alternativas**: atender tudo na EmuThread (bloquearia a emulação no I/O);
travar o núcleo por mutex (contenção e risco de deadlock com o renderer).

### D6. Reúso das APIs de núcleo existentes
**Decisão**: `NDS::SetKeyMask`, `NDS::TouchScreen`/`ReleaseScreen`,
`GPU::GetFramebuffers` e o caminho de savestate já usado pela GUI.
**Por quê**: menos código novo, comportamento consistente com a GUI.
**Alternativas**: implementar caminhos próprios — desnecessário e arriscado.

### D7. Sem push de eventos; o frame é consultado, não empurrado
**Decisão**: não expor `event.subscribe`/`event.stopped`. O único push é o do
streaming de tela (`event.frame`/`event.stream_end`), que faz parte da captura.
Progresso de execução, se um dia necessário, é consultado (poll) em vez de
empurrado.
**Por quê**: a tela é produzida a 60 fps; empurrar um evento por quadro floodaria
o agente (60 msg/s) e "frame" ≠ "a tela mudou". O halt do GDB já é sinalizado ao
cliente GDB, e `emu.pause` é iniciado por quem pausou — então `event.stopped` não
agrega no MVP. Empurrar só o que é raro/importante.
**Alternativas**: `event.subscribe` com coalescing (`every_ms`) e `event.stopped`
com gancho no núcleo (`GdbStub`) — descartados por complexidade sem necessidade
comprovada.

### D8. Carga mínima na thread de emulação
**Decisão**: nenhum trabalho pesado na EmuThread. I/O de socket, serialização
JSON e logging do tráfego ficam na thread de controle. Por quadro, a EmuThread
faz no máximo O(1) e sem alocação: o merge de input é um único AND, e os eventos
apenas **sinalizam** (flag/atomic/notify) a thread de controle, que codifica e
envia. A captura de tela é **sob demanda** — a EmuThread só copia o framebuffer
quando há pedido. Sem cliente conectado/assinante, não há trabalho por quadro.
**Por quê**: a EmuThread roda o loop de emulação; qualquer custo por quadro vira
queda de frame rate. Manter o custo O(1) e fora dela preserva o desempenho.
**Alternativas**: codificar/emitir eventos na EmuThread (simples, mas custo por
quadro); capturar o framebuffer todo frame (caro e desnecessário).

### D9. Formato de pixel e conversão
**Decisão**: a captura parte do framebuffer nativo do renderer de software, que é
32-bit **BGRA8888** (256×192 por tela, já composto). O método aceita `format`
(`bgra8` padrão, `rgba8` opcional). A conversão (swizzle BGRA→RGBA) SHALL ocorrer
fora da EmuThread, sobre a cópia; a EmuThread só copia o buffer quando uma amostra
é devida.
**Por quê**: o NDS tem paletas por camada, mas a imagem final mistura camadas e 3D
(RGB666, alpha), podendo passar de 256 cores — por isso cor plena 8bpp. Converter
fora da EmuThread respeita o orçamento de performance.
**Alternativas**: retornar indexado/paleta (incorreto para a composição); forçar
RGBA na EmuThread (custo por amostra no caminho crítico).

## Risks / Trade-offs

- **Custo por quadro na EmuThread** → *Mitigação*: merge de input O(1); eventos só sinalizam; captura sob demanda; nada por quadro sem cliente. Medir frame rate antes/depois.
- **Framebuffer indisponível no renderer OpenGL** (`GPU::GetFramebuffers` retorna
  false fora do renderer de software) → *Mitigação*: exigir/forçar o renderer de
  software para captura, ou implementar readback via GL (`glReadPixels`) numa
  fase seguinte. Documentar a limitação.
- **Savestate na EmuThread adiciona latência** → *Mitigação*: operação é rápida e
  já é feita pela GUI; medir e, se preciso, fazer em ponto seguro do loop.
- **Desincronização do frame binário** se o cliente ler errado → *Mitigação*:
  framing estrito, `Content-Length`/tamanho explícitos, e encerrar a conexão em
  violação de protocolo.
- **Segurança do socket** → *Mitigação*: Unix domain por padrão, permissões
  restritas; TCP desabilitado salvo opt-in explícito.
- **Múltiplos clientes** → *Trade-off*: permitir vários (eventos em broadcast)
  simplifica o copiloto, mas exige cuidado com estado por cliente; nesta versão,
  aceitar vários com assinatura independente.
- **Dependência `nlohmann/json`** → *Mitigação*: header-only, vendorado no repo.

## Open Questions

- Defaults de intervalo/duração/nº de amostras do streaming (ex.: 1000 ms, 10 s)
  — decidível sem mudar o spec.
- Nomes finais dos métodos (`screen.capture` vs `screen`) — ajustável sem impacto.
