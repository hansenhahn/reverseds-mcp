## Why

A segunda sessão de RE expôs falhas de **confiança** no ferramental, antes de qualquer
automação de causalidade: o gdb cria watchpoints de leitura/acesso, mas o MCP os reporta como
erro e não os lista; endereços hex/dec são conferidos à mão (já houve patch no lugar errado);
e o esgotamento de slots de hardware não diz o que está ocupado. Se a Onda 1 (breakpoints
condicionais, backtrace, hit log) for construída sobre esse alicerce, ela herda o erro.

## What Changes

- `set_watchpoint` SHALL reconhecer a resposta de sucesso do gdb para **read/access** e
  retornar o número do watchpoint (hoje devolve `error` falso).
- `list_breakpoints` SHALL listar **todos** os watchpoints (write/read/access), com número,
  tipo normalizado, endereço, condição e habilitado; `remove_breakpoint` SHALL funcionar para
  todos eles e reportar erro claro quando o número não existir.
- Nova tool `debug_slots` SHALL reportar, para o core conectado, o **limite** de watchpoints
  de hardware, quantos estão **em uso**, quantos estão **livres** e a lista por tipo.
- Falha ao criar watchpoint por falta de recursos SHALL retornar `error` + `hint` apontando
  `debug_slots`/`list_breakpoints` para liberar slots.
- Nova tool `addr_valid(value)` SHALL aceitar inteiro ou texto (`0x...`/decimal), devolver
  decimal, hex normalizado, alinhamento de 4 bytes, **região mapeada** do ARM9 e o **overlay**
  quando o endereço cair em um; entrada inválida SHALL retornar `error` + `hint`, e endereço
  não mapeado SHALL ser um resultado válido com `mapped=false`.
- `set_breakpoint` e `mem_write` SHALL ecoar o endereço normalizado no retorno (confirmação
  barata contra erro de aritmética).
- A skill do agente SHALL documentar `debug_slots`/`addr_valid` e o checklist de confiança
  (provar a escrita, não confiar em NOP, validar endereço antes de escrever).

## Capabilities

### New Capabilities
<!-- nenhuma -->

### Modified Capabilities
- `mcp-debug-tools`: o report/list/remove de watchpoints passa a cobrir read/access e adiciona
  o diagnóstico de slots de hardware.
- `mcp-re-workflows`: adiciona a validação/normalização de endereços (`addr_valid`) com
  região e overlay.

## Impact

- MCP: `infra/gdb.py` (parse de criação/listagem/remoção), `application/ports/debug.py`
  (`watchpoint_limit`, `core`), `domain/addresses.py` (novo: parse + mapa de regiões),
  `domain/debug.py` (doc do `Breakpoint.kind`), `tools/debug.py` (`debug_slots`, hints),
  `tools/re.py` (`addr_valid`), `tools/app.py` (hint de recursos), testes.
- Emulador: **nenhuma mudança**.
- Sem custo por quadro e sem mudança de comportamento de emulação.
