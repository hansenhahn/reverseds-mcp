## Context

Ver `proposal.md` — Why. O melonDS compõe os quadros internamente (`GPU`, renderer de
software e de GPU); o canal de controle já entrega o framebuffer **composto** para
captura. Falta expor o render de **uma** camada. O change é no **emulador (frontend)**,
reusando o renderer existente.

## Goals / Non-Goals

**Goals:**
- Render de uma camada isolada (engine × BG/OBJ/3D) pelo renderer do emulador.

**Non-Goals:**
- Reimplementar composição no MCP (justamente o que se quer evitar).
- Editar/enviar camadas de volta ao emulador.

## Decisions

- **Usar o renderer do melonDS** (software e/ou GPU) restrito a uma camada — o oráculo é
  o que o emulador exibe. Alternativa descartada: compor BG/OBJ/3D no script — foi o que
  falhou na sessão.
- **Interface mínima**: parâmetros `engine` (`A`/`B`) e `layer` (`bg0..bg3`/`obj`/`3d`);
  validar a combinação (nem todo engine tem 3D/BG conforme o modo).
- **Sob demanda, na `EmuThread`**, sem custo por quadro.

## Risks / Trade-offs

- [Renderizador de GPU vs software] → o alvo inicial é o renderer de software (o que a
  captura já usa); GPU como extensão.
- [Camadas que dependem de estado por-frame] → combinar com frame-control
  (`add-frame-control`) para um render determinístico.
