## Context

O melonDS já expõe: o **canal de controle** (JSON-RPC sobre Unix socket: input,
tela, savestate, pause, cart trace — ver spec `control-channel` e `cart-trace`) e
o **stub GDB** (RSP sobre TCP, ARM9:3333 / ARM7:3334). Já validamos, em
`reverse-ds`, o **`gdb-multiarch` + pwndbg** contra o stub: com
`set remote hardware-watchpoint-limit N` os watchpoints são de **hardware** de
verdade, e dá pra carregar o **`.map` de símbolos** no gdb. Ver `proposal.md` para
a motivação.

## Goals / Non-Goals

**Goals:**
- Um servidor MCP que dá ao agente: jogar/observar, depurar e **workflows de RE**.
- Reaproveitar os canais existentes; **zero mudança no emulador**.
- Tools de baixo nível (1:1 com os canais) **e** de alto nível (find_writer, diff…).

**Non-Goals:**
- Análise estática (Ghidra) — **fora** por ora.
- **Orquestrar o emulador** (subir/derrubar) — assume um emulador já rodando.
- **Streaming contínuo de tela** para o agente — captura **sob demanda** (custo de tokens).
- Modificar o emulador.
- Multi-instância do emulador (uma por vez nesta versão).

## Decisions

### D1. Servidor MCP em Python
**Decisão**: MCP em Python, reaproveitando a lógica de framing/JSON-RPC já escrita
(`control-client.py`) e um cliente RSP próprio.
**Por quê**: as ferramentas de referência já são Python; menos atrito.
**Alternativas**: outro runtime — desnecessário.

### D2. Backends: canal de controle (socket) + gdb (não RSP próprio)
**Decisão**: o MCP fala o **canal de controle** (socket) para emulação/tela/trace,
e um **gdb** (`gdb-multiarch`, com **pwndbg** e o **`.map` de símbolos** carregado)
para o debug (memória/registradores/breakpoints/watchpoints/run).
**Por quê**: o gdb nos dá **símbolos / `.map` / backtrace com nomes** — essencial
pra RE — e, com `set remote hardware-watchpoint-limit N`, faz **watchpoint de
hardware de verdade** (o fallback pra software era só config faltando). O RSP
direto exigiria reimplementar resolução de símbolos e disassembler com nomes.
**Alternativas**: cliente RSP próprio — controle total, mas **sem símbolos/backtrace**
(reimplementação) e sem a conveniência do gdb; **rejeitado**.

### D3. Duas camadas de tools
**Decisão**: tools de **baixo nível** (1:1: `input_*`, `screen_capture`,
`mem_read`, `watchpoint`, …) e de **alto nível** (compostas: `find_writer`,
`find_reader`, `state_diff`).
**Por quê**: o agente pode usar as primitivas quando precisa e os workflows
prontos para o caso comum.

### D4. `find_writer` / `find_reader` como watchpoint + run (via gdb)
**Decisão**: implementar com os watchpoints do **gdb** (`watch`/`rwatch`/`awatch`,
que emitem `Z2`/`Z3`/`Z4`), com `set remote hardware-watchpoint-limit N` já
aplicado; `continue`, esperar a parada, e retornar `PC` + registradores + backtrace
(com nomes, se houver `.map`); timeout explícito quando não há hit.
**Por quê**: é o padrão de RE, e o gdb já entrega watchpoint de hardware **e**
símbolos.
**Riscos**: a parada chega como SIGTRAP genérico (sem old/new) — o retorno do MCP
dá o PC/contexto, que é o que importa.

### D5. Tela sob demanda (não streaming) — custo de tokens
**Decisão**: `screen_capture` é **sob demanda**: o agente captura quando precisa
"olhar", uma vez por vez. **Não** expor streaming contínuo de tela ao agente.
**Por quê**: cada quadro enviado ao modelo consome **tokens de visão**; um stream
(60 fps, ou mesmo 1 fps) é insustentável em custo. O streaming do canal de controle
existe pra outros usos (viewer local, gravação), não pro agente.
**Formato**: PNG no disco + caminho; opcionalmente downscale/quantização pra
reduzir tokens quando a visão for realmente necessária.
**Alternativas**: streaming push/poll de quadros ao agente — rejeitado (tokens).

### D6. Símbolos via `.map` carregado no gdb
**Decisão**: carregar o `.map` (endereço→nome) **no gdb** (ex.: `add-symbol-file`
ou um arquivo de símbolos) e resolver endereço↔nome pelo próprio gdb (`info symbol`
/ `bt` com nomes).
**Por quê**: reaproveita o gdb em vez de reimplementar resolução; dá nomes às tools
e ao backtrace (o `.map` pode vir do Ghidra ou de descobertas).

### D7. Tradução cartucho → arquivos (FAT/FNT) — o núcleo do MCP
**Decisão**: o MCP parseia o **FNT/FAT** do NitroFS da ROM e mapeia cada offset
lido do cartucho → arquivo. É a função **central**: transforma o trace bruto em
"quais arquivos o jogo leu".
**Por quê**: offset cru não diz nada; o nome do arquivo diz. O consumidor já domina
o formato NitroFS.
**Notas**: FNT = nomes; FAT = mapeamento id→offset/tamanho. Um offset cai em um
arquivo; o MCP resolve e (opcionalmente) agrega leituras por arquivo.

## Risks / Trade-offs

- **Cliente RSP próprio** (parsing de pacotes/stop-reply) → *Mitigação*: subconjunto
  pequeno e já validado nos testes.
- **Timeouts de watchpoint** (endereço que nunca é escrito) → *Mitigação*: timeout
  explícito e mensagem clara.
- **Imagem grande para visão** → *Mitigação*: PNG em disco + opção base64/downscale.
- **Timing**: parar/continuar entre os dois canais exige cuidado → *Mitigação*:
  sequenciar as operações (não assumir estado).

## Open Questions

<!-- Resolvidas: orquestração do emulador (não), streaming de tela (não; sob demanda), Ghidra (fora). -->
