## Context

O canal de controle já transporta payloads binários (framebuffer) com framing
`Content-Length` + frame `[u32 BE N][bytes]`. O MCP já tem um parser nativo de header/FNT/FAT
e overlays (`domain/cartfs.py`, `domain/overlays.py`) e um adaptador de arquivo
(`infra/ndsrom.py`). A peça que falta é a origem dos bytes: o emulador.

## Goals / Non-Goals

**Goals:**
- O MCP ler sempre a ROM carregada no melonDS, sem caminho fixo nem bind-mount.
- Detectar troca de ROM e remontar o FS/overlays sem reiniciar o MCP.
- Manter o custo baixo: leituras sob demanda, nada por quadro.

**Non-Goals:**
- Servir a ROM inteira em uma única mensagem ou cachear a ROM inteira no MCP.
- Alterar o comportamento de emulação.
- Suportar jogos de GBA (o canal expõe o cartucho NDS).

## Decisions

- **`rom.info` + `rom.read` no canal** (em vez de um novo socket ou de reusar o GDB).
  Justificativa: reusa o framing binário existente e mantém o MCP desacoplado do caminho do
  arquivo. Alternativa descartada: montar a ROM por bind-mount (era o problema).
- **Leitura direta do buffer da ROM na thread do cliente de controle**, não na EmuThread.
  A ROM é imutável durante a execução normal; a leitura não toca no estado do núcleo e o
  guideline proíbe I/O pesado na EmuThread. Alternativa descartada: enfileirar leituras na
  EmuThread (custoso e serializaria com a emulação).
- **`rom.read` com limite de 16 MiB por chamada**; o MCP divide leituras maiores em chunks de
  4 MiB. Justificativa: evita alocações grandes vindas de um parâmetro e mantém o protocolo
  simples.
- **Identidade por `name`, `size`, `gamecode` e `checksum`**. O checksum é o mesmo CRC32
  usado pelo savestate (ARM9+ARM7) e é calculado uma vez por cartucho no `ControlServer`.
  O MCP chama `rom.info` no início de cada operação e remonta o FS quando a identidade muda.
- **Leitura sob demanda**: o MCP lê header/FNT/FAT/overlays no refresh e o conteúdo de um
  arquivo só em `cart_read`. Nada é lido por quadro.
- **`rom_info` no MCP** expõe a identidade carregada, inclusive `loaded: false` quando não há
  cartucho (sem erro).

## Risks / Trade-offs

- **Troca de ROM durante uma leitura**: carregar/ejetar o cartucho pela UI enquanto o agente
  lê pode corromper a leitura pontual. É uma ação rara e fora do fluxo de RE; o refresh no
  início da operação seguinte corrige a identidade. Não se adiciona lock por leitura no
  núcleo (impacto e escopo).
- **`rom.info` com checksum**: calculado uma vez por cartucho; trocas de ROM invalidam o
  cache por identidade. Sem custo por chamada depois do primeiro cálculo.
- **Dependência da versão do emulador**: um emulador antigo responde "method not found" e as
  tools de cartucho falham com erro claro; o deploy passa a construir o fork atualizado.
