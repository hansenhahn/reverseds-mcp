## ADDED Requirements

### Requirement: Seleção de snapshot nas tools 3D

As tools `gpu3d_state`, `gpu3d_polygons`, `gpu3d_textures` e `gpu3d_texture_dump` SHALL
aceitar `source` (`auto` padrão, `last`, `fresh`) e repassá-lo ao canal. As respostas SHALL
expor `frame`, `age_frames` e `stale` quando presentes. O docstring SHALL recomendar o fluxo
`emu_step_frame(n, snapshot=true)` seguido de leituras com `source=last` para manter o mesmo
frame entre chamadas, e SHALL alertar que o decode de textura lê a VRAM atual (texels podem
divergir do snapshot se o alvo estiver rodando).

#### Scenario: Mesmo frame entre chamadas
- **WHEN** o agente lê `gpu3d_state` e `gpu3d_polygons` com `source=last` após um passo com
  captura
- **THEN** as duas respostas trazem o mesmo `frame`

#### Scenario: Forçar captura nova
- **WHEN** o agente passa `source=fresh` com o emulador rodando
- **THEN** a tool solicita uma nova captura e devolve o `frame` correspondente

#### Scenario: Parado sem cache
- **WHEN** o alvo está parado, não há cache e o agente lê com `source=last`
- **THEN** a tool devolve `{"error", "hint"}` indicando como capturar um quadro
