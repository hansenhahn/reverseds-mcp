## 1. Domínio

- [x] 1.1 Adicionar `disasm.py` (capstone): dataclass `Instruction` e `disassemble(code, addr, mode)`
- [x] 1.2 Teste unitário com bytes conhecidos (ARM e Thumb)

## 2. Tool

- [x] 2.1 Adicionar `capstone` ao `pyproject` e reinstalar via `uv` (verificar a imagem)
- [x] 2.2 Expor `disassemble(addr, count, mode)` lendo memória pela porta `Debugger`
- [ ] 2.3 (opcional) anexar o símbolo do alvo de branches (reuso de `symbol_lookup`)

## 3. Verificação

- [x] 3.1 Teste unitário sem emulador (capstone puro)
- [ ] 3.2 Integração: parar num watchpoint e desmontar o PC

> Implementado no MCP (`domain/disasm.py` + tool `disassemble`). 3.2 depende do
> emulador com a imagem nova carregada.
