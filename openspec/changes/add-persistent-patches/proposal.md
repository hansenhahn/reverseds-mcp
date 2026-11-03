## Why

Patches de RE são escritos em **RAM** e somem quando o estado é recarregado: `savestate_load`
restaura a memória original e o reload de overlay descarta o patch. Hoje o agente precisa
reaplicar as mesmas `mem_write` à mão antes de cada tentativa — lento e sujeito a esquecer um
endereço.

Exemplos reais: o menu de status usa 6 instruções na overlay_0025; a tela Carregar usa 4
campos de dados na overlay_0000. Cada iteração de captura/teste exige reaplicar.

## What Changes

- **MCP-only:** um `PatchManager` mantém um conjunto ativo de escritas `{addr, bytes}`,
  aplica na RAM, persiste em `patches.json` e reaplica automaticamente após `savestate_load`.
- Tools: `patch_set(patches, persist=True, apply=True)`, `patch_apply()`, `patch_clear()` e
  `patch_list()`.
- No reload de **overlay**, o MCP não tem como saber sozinho (o hook `overlay_loaded` é D3);
  o agente chama `patch_apply()` explicitamente. O `savestate_load` é controlado pelo MCP e
  reaplica sozinho.
- Reutiliza o modelo `Patch` existente (validação/limites) e o `FileStore` (`/out`).

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-re-workflows`: patches de RAM persistentes/reaplicáveis + integração no `savestate_load`.

## Impact

- MCP: `application/patch_state.py` (novo), `bridge.py`, `tools/re.py`, `tools/control.py`,
  `domain/patch.py` (serialização), testes.
- Emulador: **nenhuma mudança**.
