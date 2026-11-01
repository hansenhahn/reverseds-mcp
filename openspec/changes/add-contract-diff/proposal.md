## Why

O C decompilado declara contratos (args, retorno, efeitos) que ninguém confere no runtime, e
um patch ASM pode divergir do equivalente compilado em C sem ninguém notar até o jogo quebrar.

## What Changes

- **`contract_check(addr, schema, ret_schema=None, ...)`**: arma o callsite, captura
  `r0..r3`/pilha, compara com o schema de argumentos e, opcionalmente, captura o primeiro
  retorno (breakpoint temporário em `lr`) e compara `ret_schema`; devolve `ok`, `hits` e
  `divergences`.
- **`diff_patch(asm_patch, c_equiv)`**: recebe duas listas de escritas `{addr, bytes}` (patch
  ASM e o equivalente compilado do C), lê a memória atual nas faixas tocadas, aplica os dois
  patches sobre a cópia e devolve `iguais`/`diffs` byte a byte.
- Sem mudança no emulador.

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-re-workflows`: adiciona `contract_check` e `diff_patch`.

## Impact

- MCP: `domain/contract.py`, `domain/patch.py`, `application/contract.py`,
  `application/patches.py`, `tools/re.py`, testes.
- Emulador: **nenhuma mudança**.
