## Contexto

O MCP lê memória pelo backend de debug, mas não desmonta. O agente tem usado capstone
externamente (fora do servidor), o que não é reprodutível dentro do fluxo.

## Decisões

### Biblioteca

**capstone** (madura, com wheels `manylinux`; roda no `python:3.14-slim`). Alinhado à
diretriz "preferir libs da comunidade a escrever do zero".

### Onde

- **Domínio (puro, sem I/O):** `disasm.py` com `disassemble(code: bytes, addr: int, mode) ->
  list[Instruction]` e o dataclass `Instruction(address, bytes, mnemonic, op_str)`.
- **Tool:** lê a memória pela porta `Debugger` e chama o domínio (mantém ports & adapters:
  o domínio não toca I/O).

### Modo

`arm`/`thumb` **explícito** (default `arm`). Detecção automática é ambígua (ARM/Thumb
entrelaçados, sem símbolo); não inferir — **YAGNI**.

### Simbolização

Se houver `.map` carregado (`symbol_load`), anexar o símbolo do alvo de branches (reuso de
`resolve_symbol`) a cada instrução de branch, quando aplicável.

## Riscos

- O alvo precisa estar **parado** para ler memória pelo gdb (documentar no uso).
- Limitar `count` (teto) para não puxar blocos enormes.
