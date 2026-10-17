## 1. Domínio — filesystem (puro)

- [x] 1.1 Funções de decode do header NDS (offsets de `FNT`, `FAT`, `arm9_overlay`, `arm7_overlay`). Verificar: teste unitário com um header fixture.
- [x] 1.2 Parser do `FNT` (árvore de diretórios, ids) e do `FAT` (offset/tamanho por id). Verificar: teste com fixtures reais → 765 arquivos e caminhos corretos.
- [x] 1.3 Mapeamento `offset→arquivo` e leitura de conteúdo por caminho/id. Verificar: teste com offsets conhecidos (ex.: `0x12C000` → `/data/sound_data.sdat`).

## 2. Domínio — overlays (puro)

- [x] 2.1 Parser das tabelas `y9`/`y7` (`id`, `ram_address`, `ram_size`, `bss_size`, `file_id`). Verificar: teste com fixture → 45 overlays no ARM9 e lista vazia no ARM7.
- [x] 2.2 Resolução `RAM→overlay` por intervalo. Verificar: teste (`0x021FCB40` → overlay 1) e endereço fora → nada.

## 3. Adaptador nativo (substitui o ndstool)

- [x] 3.1 Implementar a porta `CartFs` lendo a ROM diretamente (`seek`/`read`, sem subprocess). Verificar: abrir a ROM do Hotel Dusk e listar/ler.
- [x] 3.2 Conferir a saída contra o `ndstool -l` na mesma ROM (paths e offsets idênticos). Verificar: comparação sem divergências.
- [x] 3.3 Remover o subprocess e a config `ndstool_path`/`RE_MCP_NDSTOOL`. Verificar: nenhuma referência restante; `uv run pyright` limpo.

## 4. Tools MCP

- [x] 4.1 `cart_list` e `cart_read` (grava o arquivo em `/out`). Verificar: smoke com a ROM real.
- [x] 4.2 `overlay_list` e `overlay_for_address`. Verificar: smoke devolve 45 overlays e resolve um endereço de RAM.

## 5. Validação

- [x] 5.1 `uv run pyright` sem erros e `uv run python -m pytest` verde. Verificar: comandos sem erro.
- [x] 5.2 `openspec validate add-native-cartfs --strict` OK. Verificar: comando sem erro.
