## Context

Ver `proposal.md` — Why. O MCP hoje só expõe memória crua (`mcp-debug-tools`) e
workflows; **nada decodifica IO**. A arquitetura é em camadas: `domain/` (modelo +
serviços puros, sem I/O e sem portas), `application/` (serviços que **orquestram portas**
+ as portas em `application/ports/`), `infra/` (adaptadores) e `tools/` (transporte MCP).
O GBATEK (5 MB de HTML) está no repo e é a documentação referência — o próprio melonDS o
credita. O stub gdb lê IO pelo mesmo barramento da CPU (`ARM::ReadMem → BusRead`), então
valores de IO chegam ao MCP. Este change é **MCP-only**: não toca o núcleo nem o frontend
do melonDS.

## Goals / Non-Goals

**Goals:**
- Decodificação determinística do IO map a partir de um schema derivado do GBATEK.
- Tools semânticas de vídeo (`video_state`, `vram_layout`, `read_vram`).
- Testável **sem** o emulador (decode puro + fixtures).

**Non-Goals:**
- Cobrir todo o GBATEK (só o escopo inicial: vídeo/VRAM/DMA/POWCNT/DISP3DCNT).
- Frame-step, captura pausada, render de camadas, DMA trace (changes separados no fork).
- Mudar o emulador.

## Decisions

- **Schema como dados versionados no `domain/`**, não parsing do HTML do GBATEK em runtime.
  Alternativas descartadas: parsear o HTML no build/run (frágil e pesado) e RAG/prompt
  (não determinístico). O schema é a fonte da verdade e é revisável.
- **Decode puro no domínio** (`domain/io.py`: `decode_io(addr, bytes)`), sem I/O. A
  leitura de memória fica na **aplicação** (`application/io.py`), que orquestra a porta
  `Debugger` (reuso de `read_memory`) — sem mecanismo novo de acesso à memória.
- **Regras de layout de VRAM (MST→janela) puras no domínio**, separadas do I/O: a função
  recebe os valores de `VRAMCNT` e devolve banco→janela. A tool apenas lê o IO (via
  aplicação) e aplica essa função.
- **Tools finas em `tools/`** (`tools/io.py`): só parseiam argumentos, chamam a aplicação
  e serializam — a orquestração mora em `application/`, nunca no `tools/` nem no `domain/`.
- **Fonte: GBATEK**, sem camada de hipótese. Registros cuja *acessibilidade* difere no
  melonDS recebem nota: o GBATEK marca `VRAMCNT` como `(W)`, mas o melonDS expõe leitura
  (verificado por smoke test), o que permite `vram_layout()` ler o mapeamento em tempo real.
- **Duas capabilities**: `mcp-io-decode` (decode genérico de IO) e `mcp-video-tools`
  (semântica de vídeo). Alternativa descartada: uma só — misturaria decode genérico de IO
  com semântica de vídeo; a separação mantém o decode reutilizável (DMA/IRQ depois).
- **Escopo inicial conservador.** Alternativa descartada: cobrir tudo de uma vez (scope
  creep); outros registradores entram sob demanda.

## Risks / Trade-offs

- **[Tabela MST→janela] é o ponto delicado** → derivar do GBATEK **e** conferir contra o
  comportamento do `GPU.cpp`/render; é onde a sessão de RE patinou.
- [Schema divergir do melonDS em algum registro] → testes de **regressão** com fixtures
  reais (valores do smoke test); registrar acessos que diferem do spec.
- [Manter o schema à mão é esforço contínuo] → escopo inicial pequeno e âncoras por
  registro; expandir sob demanda.
- [`vram_layout()` depender do emulador expor `VRAMCNT`] → documentado na tool; em HW real
  (write-only) o caminho seria capturar writes, hoje desnecessário.
