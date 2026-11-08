## Why

Já vemos o frame, os polígonos e as texturas, mas não respondemos a pergunta
central da RE de assets: **de onde veio isso?** Para uma textura, queremos saber
qual VRAM foi usada, **qual write (DMA/CPU) a preencheu**, qual buffer de RAM foi
a origem e qual código a carregou/decodificou. Para geometria, queremos o
**display list** que alimenta o GXFIFO e os parâmetros tipados (`vtx`, `texcoord`,
matriz) — não só o `screenpos` final.

Sem essa origem, a RE para no "achei na tela". Com ela, segue para o loader/parser
no código (o nosso alvo), e a extração/importação fica para a ferramenta externa
(`kheartsds-tool`).

**Escopo:** este change para no **decomp** (observar, localizar e provar a
origem). Não cria formatos prontos, não faz parser de container, não extrai nem
importa assets.

## What Changes

- **Histórico de origem de escrita em VRAM (emulador):** ring bounded, armado sob
  demanda, que registra writes que cobrem VRAM (`dst range`, `src`, `len`, `pc`,
  `frame`, `kind=dma|cpu`). Consulta por endereço/faixa, mais recente primeiro.
- **Origem da textura (MCP):** `3d.texture_raw` devolve os bytes crus da textura
  (da VRAM de textura); `gpu3d_texture_source(index|tex_param, ...)` busca o
  **mesmo padrão na RAM** e devolve os buffers candidatos (o dado-fonte já
  descomprimido), sem depender do mapeamento textura→VRAM física. Opcionalmente
  dumpa os candidatos. A partir do buffer, um watchpoint acha o loader.
- **Origem do GXFIFO / display list (MCP):** `gxfifo_source(...)` devolve o `src`
  e o `pc` do DMA/CPU que alimenta `0x04000400` (o display list), com opção de
  dump do buffer candidato.
- **Decode tipado do trace GXFIFO (MCP):** `gxfifo_trace_read(decode="typed")`
  decodifica parâmetros em campos semânticos (`vtx` x/y/z, `texcoord` u/v,
  `mtx` elemento/modo), além do cru.
- **Busca genérica de bytes na RAM (MCP):** `find_bytes_in_ram(hex|from_buffer,
  ram_start, ram_size)` para localizar na RAM o buffer cujo conteúdo foi para
  VRAM/GXFIFO (base para achar o dado-fonte no arquivo/loader).

## Capabilities

### New Capabilities
- `mcp-3d-asset-re`: origem de textura/display list, decode tipado e busca de
  buffer.

### Modified Capabilities
- `control-channel`: histórico de writes em VRAM/GXFIFO e captura por frame.

## Impact

- Emulador: `src/DMA.cpp` (alimentar o histórico), `src/GPU3D.cpp` (origem do
  enfileiramento/display list), `src/frontend/qt_sdl/ControlServer.{h,cpp}`
  (métodos, ring, consulta), `src/NDS.h` (ponte/callbacks se necessário).
- MCP: `tools/three_d.py` (ou módulo novo `asset_re`), testes, skill.
- Custo: ring O(1) por transfer só com o histórico armado; sem assinante, zero por
  quadro. Dumps são sob demanda.

## Non-Goals

- **Nenhum formato pronto** (NSBMD/NSBTX/P2/D2KP) nem parser de container.
- **Nenhuma extração/importação** de assets (fica no `kheartsds-tool`).
- Descompressão de arquivo e hexdump de cartucho.
- Reescrever o parser do jogo; as ferramentas observam, não impõem formato.
- Reimplementar rasterização ou decodificar textura de novo (já usamos o decoder
  do renderer).
