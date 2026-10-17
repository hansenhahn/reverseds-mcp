## Why

A sessão de RE expôs atritos de **ciclo de vida** e **diagnóstico**:

- conexões mortas (ex.: emulador reiniciado) e sem health-check;
- erros ambíguos, como `screen capture timed out` (na verdade, CPU haltada);
- **snapshots em RAM** que sumiam ao reiniciar o MCP;
- contratos de erro inconsistentes, levando a ações destrutivas (matar o container).

## What Changes

- Nova tool `health_check()`: checa o canal de controle e o debugger, com dicas.
- `debug_connect()` faz uma **verificação pós-conexão** (read de teste do PC) e falha
  com hint quando o stub não responde.
- `mem_snapshot` passa a **persistir em disco** (`RE_MCP_OUT_DIR/snapshots`); `state_diff`
  lê do disco quando a captura não está em RAM (sobrevive ao restart).
- **Contrato de erro único** `{"error", "hint"?}` nas tools, com dicas para os casos
  comuns (alvo em execução, gdb não iniciado, canal indisponível).
- `screen_capture`: quando expira, retorna **hint** (CPU haltada ou renderer).

## Capabilities

### Modified Capabilities
- `mcp-bridge`: health-check, verificação de conexão, snapshots persistentes, contrato de erro.
- `mcp-control-tools`: hint de captura quando o alvo está haltado.

## Impact

- Apenas o MCP. **Nada muda no emulador.**
- Sem custo por quadro; tudo sob demanda.
