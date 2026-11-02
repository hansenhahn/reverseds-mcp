## 1. Modelo e schema

- [x] 1.1 Adicionar `write_only` a `Register`/`DecodedRegister` e propagar em
  `Register.decode`/`reg_dict`. Verificar: decode sintético preserva o flag.
- [x] 1.2 Adicionar em `domain/io/registers/video.py` (A e B): `BG0-3HOFS/VOFS`,
  `WIN0/1H/V`, `WININ`, `WINOUT`, `MOSAIC`, `BLDCNT`, `BLDALPHA`, `BLDY`, com os
  bitfields do `design.md` e `write_only=True` onde aplicável.
  Verificar: `default_registers()` cobre os endereços e cada decode sintético bate.

## 2. Tool e decode puro

- [x] 2.1 `IoReader.decode(addr, raw)` para decodificar sem debugger; `io_read(addr,
  raw=None)` usa esse caminho quando `raw` é informado.
  Verificar: `io_read(0x04001050, raw=0x... )` decodifica sem conectar no gdb.
- [x] 2.2 `io_read` inclui `write_only` e um `hint` quando `write_only && raw == 0`.
  Verificar: teste com registrador write-only e raw 0.

## 3. Validação

- [x] 3.1 `uv run python -m pytest`, `uv run pyright`, `uv run lint-imports` e
  `openspec validate add-engine-b-io-schema --strict`.
- [x] 3.2 Smoke real na engine B: `io_read` de `BGxHOFS/VOFS`, `WIN0H/V`, `WININ`,
  `BLDCNT`; conferir decode e o hint de write-only quando raw=0.

### Smoke real (2026-11-02)

- `io_read(0x04001050, raw=0x1251)` decodifica `BLDCNT_B` sem I/O.
- Leitura real na engine B: `WININ_B=0x2E2E`, `BLDCNT_B=0xAC` decodificados;
  `BG0HOFS_B`/`WIN0H_B` leram 0 e retornaram `write_only=true` + `hint`.
