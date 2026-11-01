## Context

O `args_on_hit` já captura `r0..r3`/pilha e compara um schema simples. Falta um relatório de
contrato (args + retorno) e uma forma de comparar o patch ASM com o binário gerado do C.

## Goals / Non-Goals

**Goals:**
- Validar schema de args e (opcionalmente) retorno no runtime, com divergências por campo.
- Comparar duas listas de escritas (ASM × C compilado) sobre o estado atual da memória.

**Non-Goals:**
- Compilar C dentro do MCP; `c_equiv` é o **binário/escritas** resultantes.
- Executar A/B do patch (rodar os dois e comparar comportamento); fica como follow-up.
- Múltiplos retornos de uma função; capturamos o primeiro retorno para `count=1` por chamada.
- Substituir `args_on_hit`; ele continua sendo a captura crua.

## Decisions

- **Schema no domínio.** `ArgSpec`/`Contract` saem de `application/args.py`; tipos:
  inteiro exato, `ptr`, `zero`, `nonzero`, `any`, `int:N`, `hex:N`, `eq:N`, `range:A:B`,
  `mask:M:V`. Token desconhecido é `checked=false` (não reprova).
- **Retorno por breakpoint em `lr`.** Após o hit de entrada, lemos `lr`, armamos um breakpoint
  temporário em `lr & ~1`, continuamos e lemos `r0..r3` (e o resto do contexto). Sem retorno
  no timeout → `return=null` e contrato reprovado; o breakpoint é sempre removido.
- **`count>1` com retorno** repete a captura por chamada (collect `count=1` em loop), porque o
  primeiro retorno encerra aquela invocação.
- **`diff_patch` é estático.** Aplica as escritas sobre uma cópia da memória atual (lida nas
  faixas tocadas) e compara o resultado final; detecta divergência de bytes, sobreposição e
  endereços ausentes. Não executa código — por isso é seguro e determinístico.
- **Limites.** No máximo 256 escritas e 64 KiB por patch; faixas são mescladas para leitura.
- **Sem emulador.** Só portas existentes (`Debugger`); `diff_patch` não usa savestate.

## Risks / Trade-offs

- [A/B não executado] → equivalência de bytes é necessária, mas não suficiente; o design
  registra o follow-up de rodar os patches com savestate.
- [Primeiro retorno] → funções com múltiplos `return` podem ter contratos diferentes por
  caminho; o schema deve ser o do caminho exercitado.
- [Tail call] → sem retorno para `lr`; o resultado vem `return=null` e `ok=false`.
- [Escrita sobre código] → `diff_patch` não invalida cache/emulação; é só comparação de bytes.
- [Leitura de memória] → exige debugger conectado; erro claro se não estiver.

## Migration Plan

Aditivo; novas tools. Validar com `pytest`, `pyright`, `lint-imports`, `openspec validate
add-contract-diff --strict`; smoke real opcional.
