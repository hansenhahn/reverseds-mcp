## Context

Ver `proposal.md`. O stub registra hits sem parar (`GdbStub::RecordHit`), mas o PC vem de
`Cb->ReadReg(Register::pc)` e não há largura. O `ARM.cpp` já calcula `pc_real` para
breakpoints (`R[15] - (thumb ? 2 : 4)`) e conhece a largura no `DataRead*`/`DataWrite*`.

## Goals / Non-Goals

**Goals:**
- Registrar a instrução que acessou (`pc_fault`), o endereço exato e a largura.
- Fazer o hit de DMA apontar o destino real e o `len`.
- Derivar `rmw` para `swpb`/read-modify-write sem adivinhar no emulador.
- Manter `pc`/`addr` para compatibilidade.

**Non-Goals:**
- Corrigir o caminho de stop (`Enter`/`SignalStatus`) dos watchpoints.
- Desmontar a instrução no stub; o MCP já tem `disassemble`.
- Garantir bytes exatos quando o hardware só expõe a palavra alinhada; a largura/endereço
  são o que o barramento informa.

## Decisions

### 1. `pc_fault` calculado no `ARM.cpp`

`DataRead*`/`DataWrite*` chamam `GdbCheckD` antes do acesso. Eles passam
`R[15] - ((CPSR & 0x20) ? 2 : 4)` (mesmo cálculo do `GdbCheckC`) e a largura (1/2/4).
`CheckWatchpt` registra `pc`, `pc_fault`, `addr` e `width`.

**Alternativa:** usar só `Cb->ReadReg(pc)` e subtrair no MCP; descartado porque o callback
pode variar com o pipeline/Thumb e o dado já está disponível no CPU.

### 2. Largura por função de acesso

`DataRead8`/`DataWrite8` → 1; `DataRead16`/`DataWrite16` → 2; `DataRead32`/`DataWrite32`/
`...32S` → 4. O DMA registra `len`.

### 3. DMA grava o destino real

`CheckDmaWatchpt` já recebe `addr` (destino) e `len`; o log passa a gravar `addr` (não
`search->addr`) e `width=len`, com `kind=dma-write` e `pc_fault=pc`.

### 4. `rmw` derivado no MCP

O stub grava `rmw=false` (não sabe o futuro). O MCP correlaciona hits: se houver `read` e
`write` com o mesmo `pc_fault` e `access_addr`, marca `rmw=true` nos dois. Isso cobre
`swpb` sem decodificar opcode no C++ e sem falso positivo de `ldr`/`str` separados (PCs
diferentes).

### 5. Compatibilidade

`HitRecord` mantém `pc` e `addr`; o JSON ganha campos aditivos. Clientes antigos do MCP
continuam lendo `pc`/`addr`/`kind`.

## Risks / Trade-offs

- [PC faulting errado em Thumb/IT] → usar o mesmo cálculo do breakpoint e validar no smoke.
- [DMA hit com `addr` real muda o significado antigo] → `addr` de DMA agora é o destino real;
  documentar e manter `width` como `len`.
- [`rmw` com pares read/write legítimos no mesmo PC] → instrunções que leem e escrevem o
  mesmo endereço no mesmo PC são RMW por definição; marcar é correto.
- [Clientes antigos] → campos novos são aditivos.

## Migration Plan

Rebuild do emulador + MCP; sem migração de dados. Validar com `pytest`, `pyright`,
`lint-imports`, build do emulador e smoke com `swpb`/store conhecido.

## Open Questions

- Expor `pc_fault` também no stop (`find_writer`)? (Follow-up.)
- Marcar `rmw` para `ldrex`/`strex` de PCs diferentes? (Fora do escopo; exigiria correlação
  mais ampla.)
