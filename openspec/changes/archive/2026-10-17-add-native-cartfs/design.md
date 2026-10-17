## Context

Ver `proposal.md` — Why. Hoje `infra/nitrofs.py` chama o `ndstool -l` por subprocess e a
config expõe `RE_MCP_NDSTOOL`; a porta `CartFs` só tem `file_count` e `file_for_offset`.
Os formatos vêm do **ndstool** (não inferidos): header em `header.h`, FNT/FAT em
`ndsextract.cpp:33-160`, overlays em `overlay.h`. Confirmei o parsing direto na ROM do
Hotel Dusk: header→`FNT 0x127200/10277`, `FAT 0x129C00/6480` (810 entradas), `arm9_overlay
0x97600/1440` (45 overlays), `arm7_overlay` vazio; 765 arquivos de FS, com os overlays
ocupando os ids `0..44` da mesma FAT. Arquitetura: hexagonal (domínio puro + portas),
Python 3.14, `uv`, `pyright`. MCP-only.

## Goals / Non-Goals

**Goals:**
- Parser nativo do FS (`header`/`FAT`/`FNT`): árvore, `offset→arquivo`, conteúdo.
- Parser nativo dos overlays (`y9`/`y7`) e resolução `RAM→overlay`.
- Remover a dependência do `ndstool`.

**Non-Goals:**
- *Escrever* ROMs (extração/empacotamento do `ndstool`), banner/ícone/CRC, extras DSi.
- Mudar o emulador.

## Decisions

- **Duas capabilities**: `cartfs` (FS) e `nds-overlays` separada. Ciclos de vida e usos
  distintos (asset vs código/RAM). Alternativa descartada: tudo em `cartfs` — mistura
  conceitos e dificulta reuso do overlay no debug.
- **Porta `CartFs` mantida e estendida** (listar/conteúdo), com a implementação nativa no
  lugar do subprocess do `ndstool`. Reuso da abstração existente.
- **Separar decode puro (domínio) da leitura de arquivo (infra)**: funções que transformam
  bytes em estruturas ficam no domínio (testáveis sem ROM/emulador); o adaptador lê o ROM.
  Alternativa descartada: parser só na infra — perde a testabilidade sem I/O.
- **Leitura sob demanda** no arquivo da ROM (`seek`/`read`), com `header`/`FAT`/`FNT`
  cacheados em memória (poucos KB). Alternativa descartada: `mmap` de 128 MB — desnecessário.
- **Overlays a partir do header** (`arm9_overlay`/`arm7_overlay`), não procurando `y9.bin`;
  mesma fonte que o `ndstool`. Resolução por intervalo `[ram_address, +ram_size)`.
- **Tools**: `cart_list`, `cart_read` (grava em `/out`), `overlay_list`, `overlay_for_address`;
  `cart_file` permanece. **Remover** `ndstool_path`/`RE_MCP_NDSTOOL`.

## Risks / Trade-offs

- [Detalhes de formato (máscara `dir_id & 0xFFF`; ids começando em `top_file_id`; overlays na
  FAT)] → portar 1:1 do `ndstool` e cobrir com testes de regressão (fixtures do parsing real).
- [Remover `RE_MCP_NDSTOOL` é mudança de config] → documentar; se a variável existir, é
  simplesmente ignorada.
- [ROM grande] → só regiões necessárias são lidas; `FAT`/`FNT` são pequenos e ficam em cache.
