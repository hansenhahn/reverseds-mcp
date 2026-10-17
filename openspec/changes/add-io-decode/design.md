## Context

Ver `proposal.md` — Why. O MCP hoje só expõe memória crua (`mcp-debug-tools`) e
workflows; **nada decodifica IO**. A arquitetura é hexagonal (domínio puro + portas
`Protocol`; adaptadores em `infra/`). O GBATEK (5 MB de HTML) está no repo e é a
documentação referência — o próprio melonDS o credita (`README.md`). O stub gdb lê IO
pelo mesmo barramento da CPU (`ARM::ReadMem → BusRead`), então valores de IO chegam ao
MCP. Este change é **MCP-only**: não toca o núcleo nem o frontend do melonDS.

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

- **Schema como dados versionados**, não parsing do HTML do GBATEK em runtime.
  Alternativas descartadas: parsear o HTML no build/run (frágil e pesado) e RAG/prompt
  (não determinístico). O schema é a fonte da verdade e é revisável.
- **Fonte: GBATEK**, sem camada de hipótese. Registros cuja *acessibilidade* difere no
  melonDS recebem nota: o GBATEK marca `VRAMCNT` como `(W)`, mas o melonDS expõe leitura
  (verificado por smoke test), o que permite `vram_layout()` ler o mapeamento em tempo real.
- **Decode puro no domínio** (`decode_io(addr, bytes)`), sem I/O; os adaptadores só trazem
  bytes. Reuso da porta `Debugger` (`read_memory`) para `io_read`/`read_vram`. Sem
  mecanismo novo de acesso à memória.
- **Duas capabilities**: `mcp-io-decode` (decode genérico de IO) e `mcp-video-tools`
  (semântica de vídeo). Alternativa descartada: uma só — misturaria decode genérico de IO
  com semântica de vídeo; a separação mantém o decode reutilizável (DMA/IRQ depois).
- **Escopo inicial conservador.** Alternativa descartada: cobrir tudo de uma vez (scope
  creep); outros registradores entram sob demanda.

## Risks / Trade-offs

- [Schema divergir do melonDS em algum registro] → testes de **regressão** com fixtures
  reais (valores do smoke test); registrar acessos que diferem do spec.
- [Manter o schema à mão é esforço contínuo] → escopo inicial pequeno e âncoras por
  registro; expandir sob demanda.
- [`vram_layout()` depender do emulador expor `VRAMCNT`] → documentado na tool; em HW real
  (write-only) o caminho seria capturar writes, hoje desnecessário.
