## Why

Hoje o mapeamento offset→arquivo depende do **`ndstool`** (subprocess `-l`): acopla o MCP
a um binário externo (config `RE_MCP_NDSTOOL`), exige instalá-lo no contêiner e só oferece
listagem. Os formatos FNT/FAT e as tabelas de overlay (`y9`/`y7`) são simples e estáveis;
portá-los para Python remove a dependência e destrava o que o `ndstool` não dava: **ler o
conteúdo** de um arquivo e **resolver endereço de RAM → overlay** (útil no debug).

## What Changes

- Parser nativo (Python) do **filesystem de cartucho**: header NDS → `FAT`/`FNT`, com
  árvore de arquivos, `offset→arquivo` e **conteúdo** de arquivo.
- Parser nativo das **tabelas de overlay** `y9` (ARM9) e `y7` (ARM7): `id`, `ram_address`,
  `ram_size`, `bss_size`, `file_id`; e resolução **endereço de RAM → overlay**.
- Tools MCP: listar o FS, ler um arquivo (→ diretório `/out`), listar overlays e resolver
  `RAM→overlay`.
- **Remove a dependência do `ndstool`** (subprocess e config `RE_MCP_NDSTOOL`).
- MCP-only; **nada muda no emulador**.

## Capabilities

### New Capabilities
- `cartfs`: filesystem nativo do cartucho (header/`FAT`/`FNT`) — árvore, `offset→arquivo`
  e conteúdo.
- `nds-overlays`: tabelas `y9`/`y7` — overlays (`id`, RAM, tamanho, `bss`, `file_id`) e
  resolução de endereço de RAM → overlay.

### Modified Capabilities
- `mcp-re-workflows`: expõe as tools de FS (listar/ler) e de overlays (listar/resolver),
  sem depender de ferramenta externa.

## Impact

- MCP: substitui `infra/nitrofs.py` (que chama o `ndstool`) por um parser nativo; remove
  `ndstool_path` da config. Sem dependência nova; leitura sob demanda (sem custo por quadro).
