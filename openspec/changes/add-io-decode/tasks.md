## 1. Schema e decode (domínio puro)

- [ ] 1.1 Definir o schema do IO map como dados versionados (escopo: vídeo 2D/OAM/paletas, `VRAMCNT`/`WRAMCNT`, `DMA`, `POWCNT1`, `DISP3DCNT`). Verificar: revisão contra o GBATEK e script que carrega o schema sem erro.
- [ ] 1.2 Implementar `decode_io(addr, bytes)` puro (bitfields/enums a partir do schema). Verificar: testes unitários com vetores conhecidos.
- [ ] 1.3 Testes de regressão com fixtures reais do smoke test (`DISPCNT=0x4001111D`, `POWCNT1=0x020F`, `DISP3DCNT=0x19`, `VRAMCNT A..I`). Verificar: `pytest` verde.

## 2. Tool de leitura de IO

- [ ] 2.1 Tool `io_read(addr)`: lê pela porta `Debugger`, exige alvo parado e devolve valor bruto + campos; erro com hint se alvo em execução/endereço fora do IO. Verificar: unit test com `Debugger` mockado.
- [ ] 2.2 Smoke com emulador: `io_read(0x04000000)` e `io_read(0x04000240)`. Verificar: valores batem com o smoke test documentado.

## 3. Domínio de vídeo

- [ ] 3.1 `video_state(engine)`: estado decodificado (`DISPCNT`/`BGxCNT`/`POWCNT`/`DISP3DCNT`, top/bottom). Verificar: unit test com `Debugger` mockado.
- [ ] 3.2 `vram_layout()`: resolve banco→janela a partir do `VRAMCNT` atual. Verificar: unit test com fixture de `VRAMCNT` → janelas esperadas.
- [ ] 3.3 `read_vram(...)`: lê bytes de banco/janela. Verificar: unit test com mock + smoke manual (`0x06600000`).

## 4. Exposição e validação

- [ ] 4.1 Expor `io_read`, `video_state`, `vram_layout`, `read_vram` no server MCP. Verificar: agente lista as tools.
- [ ] 4.2 Smoke end-to-end com emulador ligado. Verificar: saídas batem com os valores do smoke test.
- [ ] 4.3 `uv run pytest` verde e `openspec validate add-io-decode` OK. Verificar: comandos sem erro.
