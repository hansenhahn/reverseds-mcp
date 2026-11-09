## Context

Ver `proposal.md` — Why. O cartucho já expõe o buffer imutável da ROM e um ponto único de
leitura de dados: `NDSCartSlot::Interface::ROMReceiveData` chama `CartCommon::ROMCommandReceive`,
que chama `CartCommon::ROMRead32` (`src/NDSCart/CartCommon.cpp`). CPU e DMA do cartucho passam
por esse caminho; `rom.read` e `Checksum()` leem `GetROM()` diretamente.

O MCP já parseia FNT/FAT nativamente (`domain/cartfs.py`) e conhece o range de cada arquivo
(`NdsFs.span`). O que falta é um caminho para servir bytes alternativos durante a leitura do
cartucho e a superfície de controle para registrar/recarregar esses bytes.

## Goals / Non-Goals

**Goals:**
- Servir o override em **todas** as leituras de dados do cartucho (CPU e DMA), inclusive
  palavras de 4 bytes que cruzam o início/fim do range.
- Custo zero de comportamento e ~1 leitura atômica por acesso quando não há override.
- Publicação segura de um novo buffer durante o hot reload, sem leitura parcial.
- UM contrato genérico por range, reutilizável por qualquer cliente (não só NitroFS).

**Non-Goals:**
- Virtualizar o tamanho do arquivo no FAT/FNT.
- Override por sub-recurso/entry de containers (P2/CAKP/D2KP/KAPH).
- Alterar `rom.read`/`Checksum()`/savestate ou a imagem da ROM em disco.
- Resolver FNT/FAT no emulador (o MCP já faz isso).

## Decisions

- **Hook em `CartCommon::ROMRead32()` (core), não no frontend.** É o único ponto onde os bytes
  são efetivamente lidos e é compartilhado por CPU e DMA. Alternativas descartadas: hook em
  `NDSCartSlot::Interface` (só vê o endereço de início/length, não os bytes) e hook só em
  `rom.read` (não afeta a emulação). Como isso toca `src/`, a mudança é justificada por ser o
  ponto obrigatório de intercepção de leitura.
- **Registro de overrides por instância de `CartCommon`, não global.** Fica isolado por
  cartucho e é destruído junto com ele na troca/ejecção, sem ranges órfãos. Alternativa
  descartada: registro global no `ControlServer` (exigiria limpeza manual e poderia servir
  bytes do cartucho antigo).
- **Fast path com `std::atomic<bool>` + `std::mutex`.** Sem override ativo, `ROMRead32` faz
  apenas uma leitura atômica relaxada e segue o caminho original. Com overrides ativos, o
  mutex protege o vetor e a busca por range; não há alocação por leitura. Alternativas
  descartadas: `shared_mutex`/snapshot atômico (mais complexidade e custo por operação) e
  cópia imutável por leitura (alocação proibida no caminho quente).
- **SET/RELOAD leem o arquivo do host na thread do controle e só então bloqueiam o mutex** para
  trocar o buffer. A EmuThread nunca faz I/O nem serialização.
- **MCP resolve `path` → `[start, end)` e envia o range absoluto.** Reusa o parser FNT/FAT já
  testado; evita duplicar a travessia de FNT em C++. Alternativa descartada: resolver no
  emulador (mais código de núcleo e risco de divergência com o parser do MCP).
- **Semântica de tamanho pelo FAT**: o jogo conhece `end - start`; bytes além do arquivo do
  host são zero-fill; bytes além de `end` no host são ignorados. Recomenda-se repack com o
  mesmo tamanho.
- **Overrides não são serializados em savestate.** Carregar um savestate não os desfaz; `clear`
  é explícito. Na troca de cartucho eles desaparecem junto com o `CartCommon`.
- **`rom.read` ignora overrides** para preservar a extração fiel do asset original; a prova de
  que o jogo leu o override é o contador `stats`.

## Risks / Trade-offs

- **Palavra de 4 bytes cruzando o limite do range** → resolver byte a byte no caminho com
  override, consultando o range a cada byte e caindo no `ROM[]` original fora dele.
- **Reload concorrente com leitura** → novo vetor é montado e validado fora do mutex; a troca é
  um `std::move` sob lock. Leitores veem o buffer antigo ou o novo, nunca meio preenchido.
- **`host_path` invisível no processo do emulador (Docker)** → documentar que o caminho é
  resolvido pelo emulador; erro explícito `host file missing`.
- **Endereço de leitura mascarado por `ROMMask`/tradução de endereços** → o range é sempre
  comparado com o offset final (`addrhi | addrlo`), o mesmo usado no `ROM[]`.
- **Região criptografada (KEY1/KEY2)** → o override substitui o mesmo offset que o `ROM[]`
  expõe ao hardware emulado; a criptografia de comando continua por conta do cartucho.
- **Checksum/identidade da ROM** → `Checksum()` lê a imagem original; a identidade não muda.

## Migration Plan

1. Emulador: build do fork com os métodos novos; clientes antigos do canal continuam
   funcionando (métodos novos são aditivos).
2. MCP: tools novas aparecem no `list_tools`; sem override ativo nada muda.
3. Rollback: remover os dois lados; overrides não persistem em disco.

## Open Questions

- Nenhuma que altere specs/abordagem; a política de "mesmo tamanho" pode virar validação
  opcional num follow-up.
