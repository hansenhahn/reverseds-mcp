# mcp-video-tools Specification

## Purpose

Responde às perguntas típicas de vídeo do NDS em alto nível — estado dos engines,
mapeamento de bancos de VRAM e leitura de VRAM — usando o schema de IO decodificado.

## Requirements

### Requirement: Estado de vídeo por engine

O MCP SHALL expor `video_state(engine)` que devolve o estado decodificado do engine
(`A` ou `B`), indicando top/bottom e os campos relevantes de `DISPCNT`, `BGxCNT` e
`POWCNT`/`DISP3DCNT`.

#### Scenario: Estado do engine A
- **WHEN** o agente pede o estado do engine A com o alvo parado
- **THEN** recebe os campos decodificados (modo, BG habilitados/3D, OBJ), com top/bottom

### Requirement: Mapeamento de VRAM

O MCP SHALL expor `vram_layout()` que resolve, a partir do `VRAMCNT` **atual**, o
mapeamento banco→janela (BG/OBJ por engine, 3D, etc.).

#### Scenario: Resolver as janelas ativas
- **WHEN** o agente pede o layout com o alvo parado
- **THEN** recebe quais janelas de endereço estão ativas e qual banco as funda

### Requirement: Leitura de VRAM

O MCP SHALL expor `read_vram(...)` para ler bytes de um banco ou de uma janela de VRAM.

#### Scenario: Ler uma janela
- **WHEN** o agente pede os bytes de uma janela de VRAM (ex.: OBJ do engine B)
- **THEN** recebe os bytes correspondentes
