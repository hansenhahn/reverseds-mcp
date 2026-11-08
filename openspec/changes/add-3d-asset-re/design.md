## Context

Ver `proposal.md` — Why. Estado atual:

- O canal já tem `dma.trace` (`DMA::Start` → `NDS.OnDmaTransfer`) e o trace do
  GXFIFO (`GPU3D::WriteToGXFIFO` → `NDS.OnGXCommand`), ambos bounded e armados sob
  demanda.
- `3d.textures`/`3d.texture` já dão `TexParam`/`TexPalette`, formato/tamanho e os
  pixels decodificados; `3d.polygons` dá `screenpos`/UV.
- `vram_layout` resolve `VRAMCNT` em bancos; `dma_source` já filtra DMA por
  destino durante uma janela.
- `find_writer`/`hit_log` cobrem writes de CPU; `mem_read`/`mem_dump_file` leem RAM.

O que falta é a **ligação causal** VRAM → write → buffer de RAM → loader, sem
depender de acertar a janela de tempo do trace.

## Goals / Non-Goals

**Goals:**

- Responder "qual write preencheu esta VRAM/textura?" mesmo depois do fato (ring
  armado), com `src`, `len`, `pc`, `frame` e `kind`.
- Responder "qual display list alimenta o GXFIFO?" e dumpar o buffer candidato.
- Decode tipado do stream GXFIFO (vtx/texcoord/matriz) para reconstruir geometria.
- Localizar um buffer na RAM a partir do que foi para VRAM/GXFIFO.
- Manter custo zero sem histórico armado; nada de parser de formato.

**Non-Goals:**

- Formatos prontos/parser de container, descompressão, extração/importação.
- Reescrever o loader do jogo; a ferramenta só observa e localiza.
- Histórico ilimitado: é um ring bounded, armado sob demanda.

## Decisions

- **Histórico de origem como ring bounded, armado à mão.** Guarda
  `{dst_lo, dst_hi, src, len, pc, frame, kind}`. Escrita O(1); sem armado, zero
  custo por quadro. Alternativa descartada: manter mapa de "último escritor" por
  byte (memória/custo altos).
- **Consulta por sobreposição de faixa, mais recente primeiro.** Params
  `addr`, `len`, `max_age_frames`, `max_hits`. Se nada casar, responder
  `unknown` (com dica de armar o histórico), nunca adivinhar.
- **v1 cobre DMA; CPU via hit log/watchpoint.** Texturas/display lists costumam vir
  por DMA; writes de CPU já são observáveis com `set_watchpoint` + `hit_log`.
  Alternativa descartada: instrumentar todo store no caminho da CPU (custo alto).
- **Origem da textura por conteúdo (não por mapeamento de VRAM).** `3d.texture_raw`
  lê os bytes crus da textura direto de `VRAMFlat_Texture` (via
  `MakeVRAMFlat_TextureCoherent`); `gpu3d_texture_source` busca o **mesmo padrão**
  na RAM. Isso evita a tradução textura→VRAM física (bancos/mapeamento ambíguo) e
  acha diretamente o buffer já descomprimido. Alternativa descartada: casar com o
  `dst` do DMA via layout de VRAM (frágil e não cobre tudo).
- **Sem origem por DMA para textura; o histórico cobre GXFIFO/VRAM.** O histórico
  de writes serve para display list e faixas de VRAM; a textura usa conteúdo +
  `find_bytes_in_ram`. Os dois caminhos são complementares.
- **Dump dos candidatos sob demanda.** Com os endereços achados, o MCP lê a RAM
  (chunked) e salva `.bin` em `/out`; um watchpoint nesse endereço acha o loader.
- **Decode tipado no cliente.** A tabela de comandos já existe; decodificar
  `vtx_16`/`vtx_10`/`vtx_xy`/... e `texcoord`/matriz no `read`, fora da EmuThread.
- **Busca de bytes no MCP, com limite.** `find_bytes_in_ram` lê faixas em blocos
  (cap configurável) e devolve endereços; se necessário, evoluir para um
  `mem.search` no emulador (fast path) depois.
- **Sem captura por frame nesta versão.** Animação fica para um change separado;
  não é pré-requisito da origem.

## Risks / Trade-offs

- [Histórico não armado na hora do upload] → responder `unknown` + hint para
  recarregar a cena com o histórico ligado; nunca inventar origem.
- [Textura comprimida/decodificada em RAM] → `3d.texture_raw` cobre formatos
  não comprimidos; compressed (4x4) fica como follow-up. A busca acha o buffer já
  descomprimido; para o arquivo, seguir o loader com watchpoint (RE no código).
- [Padrão de textura colide na RAM] → devolver todos os candidatos (até
  `max_hits`), com tamanho/digest; o agente valida com dump e watchpoint.
- [Busca grande na RAM] → cap + blocos; documentar o custo.
- [Ring enche] → drops contados; o agente reinicia a captura.

## Migration Plan

Aditivo. Sem histórico armado, nenhum custo por quadro novo. Tools novas não
alteram as existentes. Validar com build do fork, `pytest`/`pyright`/
`lint-imports`, `openspec validate --strict` e smoke real numa cena 3D do KH
(achar o buffer de origem de uma textura e a display list).

## Open Questions

- Incluir writes de CPU no ring por padrão (via hook de IO a VRAM) ou manter só
  DMA + hit log?
- `mem.search` no emulador (rápido) vale o custo, ou o MCP chunked basta?
- Texturas comprimidas (4x4) para o `texture_raw`: implementar quando aparecer.
- Captura por frame (animação) fica para um change separado.
