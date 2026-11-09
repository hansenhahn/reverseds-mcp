## 1. Emulador — hook de leitura

- [x] 1.1 Adicionar a API de override em `CartCommon` (registrar/remover/recarregar/limpar e
  listar) com `start`, `end`, `host_path`, buffer, tamanho e contadores; validar `start < end`
  e `end <= ROMLength` e rejeitar sobreposição. Verificar: build OK e teste manual pela API com
  range válido, invertido e sobreposto.
- [x] 1.2 Interceptar `CartCommon::ROMRead32` com um fast path `std::atomic<bool>`: sem
  override, executar o caminho original; com override, servir byte a byte o range (incluindo
  palavras que cruzam o limite) e aplicar zero-fill quando o host for menor. Verificar: build
  OK e leitura de um range de teste devolve os bytes do host e zeros na cauda.
- [x] 1.3 Garantir que o registro de overrides pertence ao `CartCommon` e é descartado na
  troca/ejecção do cartucho (sem serialização em `DoSavestate`). Verificar: registrar override,
  trocar de ROM e confirmar que `list` volta vazio.
- [x] 1.4 Compilar o fork do melonDS. Verificar: `cmake --build` sem erros.

## 2. Emulador — comandos do canal

- [x] 2.1 Implementar `cart.override.set` no `ControlServer`: ler `host_path` com
  `ReadFileBytes` (thread do controle), validar bounds/sobreposição, chamar a API do cartucho
  e devolver `start`, `end` e `host_size`. Verificar: chamada manual no socket registra e lista
  o override; arquivo ausente e range fora da ROM retornam erro.
- [x] 2.2 Implementar `cart.override.clear`, `cart.override.list`, `cart.override.reload` e
  `cart.override.stats`, com os campos de `stats` (leituras/bytes) e erros explícitos.
  Verificar: ciclo completo set → list → reload → stats → clear pela conexão de controle.
- [x] 2.3 Fazer o `reload` montar o buffer fora do mutex e só trocá-lo sob lock, e confirmar
  que a EmuThread não faz I/O do arquivo do host. Verificar: revisão do caminho + reload
  enquanto o jogo lê o range, sem crash/corrupção.

## 3. MCP — porta e serviço de aplicação

- [x] 3.1 Adicionar `span(path)` à porta `CartFs` e ao adaptador `ChannelRom`, devolvendo o
  `FatEntry` ou `None`. Verificar: `uv run python -m pytest tests/test_cartfs.py` verde e
  `uv run pyright` sem erro.
- [x] 3.2 Criar `application/cart_override.py` que resolve `path` → `span`, chama
  `cart.override.*` e traduz "arquivo não encontrado no FS" em erro de domínio. Verificar:
  teste unitário com canal/FakeCartFs para set/clear/list/reload/stats e caminho ausente.
- [x] 3.3 Expor o serviço no `Bridge` e criar `tools/cart_override.py` com as cinco tools,
  registrando-as em `tools/server.py`; mapear `ControlError` para `{"error", "hint"?}`.
  Verificar: `list_tools` contém as cinco tools e teste de `test_tools.py` verde.

## 4. Testes e validação

- [x] 4.1 Testes do serviço/tools com fakes (parâmetros exatos, propagação de erro do
  emulador, `rom_start`/`rom_end` corretos). Verificar: `uv run python -m pytest` verde.
- [x] 4.2 Rodar os checks do MCP e validar a spec. Verificar: `uv run pyright`, `uv run
  lint-imports`, `uv run python -m pytest` e `openspec validate add-nitrofs-file-override
  --strict` verdes.
- [ ] 4.3 E2E no-op com `/mi/wd/wd_tt` (cópia idêntica): registrar, recarregar a cena e
  confirmar `hits > 0` sem regressão visual. Verificar: stats e captura de tela.
- [ ] 4.4 E2E de mudança visível: patchear um byte seguro na entry do letreiro, servir e
  recarregar a cena; confirmar mudança na captura. Verificar: comparação baseline × patched.
- [ ] 4.5 E2E sem savestate: repetir o override em boot limpo da ROM. Verificar: override ativo
  no caminho real de load.

## 5. Documentação

- [x] 5.1 Atualizar `README.md` (tools novas), `ROADMAP.md` e referenciar este change em
  `docs/nitrofs-file-override.md`. Verificar: `rg cart_override` encontra README/ROADMAP.
