## ADDED Requirements

### Requirement: Validação e normalização de endereços

O MCP SHALL oferecer `addr_valid(value)` que aceite inteiro ou texto em hexadecimal (`0x...`)
ou decimal e devolva o valor decimal, o hexadecimal normalizado, se está alinhado a 4 bytes, a
região de memória do ARM9 que o contém (quando houver) e o overlay correspondente (quando o
endereço cair em um). Texto inválido SHALL retornar `error` + `hint`; endereço fora de
qualquer região conhecida SHALL ser um resultado válido com `mapped=false`. A tool não SHALL
escrever memória nem alterar o estado da emulação.

#### Scenario: Hexadecimal válido
- **WHEN** o agente valida `"0x020A2D90"`
- **THEN** recebe o decimal correspondente, o hex normalizado, alinhamento e a região de RAM
  principal

#### Scenario: Decimal válido
- **WHEN** o agente valida um inteiro decimal dentro da RAM
- **THEN** recebe o mesmo endereço em hexadecimal e a região correta

#### Scenario: Endereço em overlay
- **WHEN** o agente valida um endereço coberto por um overlay do ARM9
- **THEN** o resultado inclui o overlay e o offset dentro dele

#### Scenario: Texto inválido
- **WHEN** o agente informa um texto que não é hexadecimal nem decimal
- **THEN** o MCP retorna `error` + `hint` com o formato aceito

#### Scenario: Endereço não mapeado
- **WHEN** o agente valida um endereço que não pertence a nenhuma região conhecida do ARM9
- **THEN** o resultado indica que não está mapeado (sem erro de execução)
