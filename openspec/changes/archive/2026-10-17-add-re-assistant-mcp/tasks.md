## 1. Ponte (bridge)

- [x] 1.1 Criar o esqueleto do servidor MCP em `reverse-ds` (transporte stdio) e verificar que um cliente MCP consegue listar as tools
- [x] 1.2 Implementar a conexão ao canal de controle (socket configurável) com erro claro quando o emulador não está rodando, e verificar com `ping`
- [x] 1.3 Implementar o backend de debug via **gdb** (subir `gdb-multiarch` conectado ao stub do core escolhido, com o limite de watchpoint de hardware aplicado) e verificar lendo o PC
- [x] 1.4 Implementar a escolha de core e o gerenciamento de erro/reconexão dos backends, e verificar trocando entre ARM9 e ARM7

## 2. Tools de controle

- [x] 2.1 Expor tools de input (key/touch/release/merge) e verificar que refletem no emulador (KEYINPUT/EXTKEYIN)
- [x] 2.2 Expor a tool de captura de tela (pontual) salvando PNG e verificar a imagem
- [x] 2.3 Expor tools de savestate e pause/resume e verificar salvar/restaurar e congelar/retomar
- [x] 2.4 Expor tools de trace de cartucho (start/stop/obter lotes) e verificar a captura de leituras

## 3. Tools de depuração

- [x] 3.1 Expor leitura/escrita de memória e verificar lendo e escrevendo um endereço
- [x] 3.2 Expor leitura/escrita de registradores e verificar o PC
- [x] 3.3 Expor breakpoints (código) e watchpoints (leitura/escrita/acesso) e verificar a parada por watchpoint de escrita
- [x] 3.4 Expor controle de execução (continue/step/interrupt) e verificar interromper durante a execução

## 4. Workflows de RE

- [x] 4.1 Implementar `find_writer` (watchpoint de escrita + run + PC/contexto) e verificar encontrando o escritor de um endereço conhecido
- [x] 4.2 Implementar `find_reader` (watchpoint de leitura) e verificar encontrando o leitor de um endereço
- [x] 4.3 Implementar o diff de estado (memória/savestate) e verificar destacando o que mudou
- [x] 4.4 Implementar o carregamento de `.map` e a resolução endereço↔nome e verificar um lookup
- [x] 4.5 Implementar o mapeamento NitroFS (offset→arquivo) e verificar correlacionando leituras do trace com um arquivo

## 5. Integração

- [x] 5.1 Rodar um fluxo de RE ponta-a-ponta (achar quem escreve num endereço durante o jogo) e verificar o resultado
- [x] 5.2 Documentar o MCP (uso, config, tools) em `reverse-ds` e verificar que as instruções sobem o servidor
