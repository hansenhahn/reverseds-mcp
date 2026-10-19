## MODIFIED Requirements

### Requirement: Registro decodificado de cada DMA

O sistema SHALL registrar, no **início** de cada transferência de DMA, um item
**decodificado**: o `cpu` (ARM9/ARM7) que programou o canal, o `channel`, o **de → para**
(`source`/`destination` — endereços e controles), o `length` em **bytes** e o **controle
decodificado** do `DMAxCNT` — pelos **mesmos nomes de campo do schema GBATEK**
(`transfer_32bit`, `src_control`, `dest_control`, `start_timing`, `repeat`, `irq`, `enable`) —
além do `pc` da **instrução que programou o canal** (o store em `DMAxCNT`), não o `R[15]`
pós-incremento. O item NÃO SHALL expor o `cnt` como bits crus.

#### Scenario: Uma transferência gera um item decodificado
- **WHEN** um canal DMA inicia uma transferência
- **THEN** um item com `cpu`, `channel`, `source`/`destination` (endereços + controles),
  `length` (bytes), `size`/`start_timing`/`repeat`/`irq` e `pc` é registrado

#### Scenario: De → para abstraído
- **WHEN** um DMA copia da RAM para a VRAM
- **THEN** o item traz `destination.address` em `0x06000000+` e o controle de destino
  (`inc`/`dec`/`fixed`/`inc/reload`) já decodificado

#### Scenario: Controle pelos mesmos nomes do schema
- **WHEN** o `DMAxCNT` é registrado
- **THEN** os campos usam os mesmos nomes do schema GBATEK (`transfer_32bit`,
  `start_timing`, ...), consistentes com o `io_read`

#### Scenario: Granularidade por transferência
- **WHEN** um DMA move um bloco de N bytes
- **THEN** é gerado **um** item (não um por palavra movida)

#### Scenario: Core e PC da instrução que programou o canal
- **WHEN** a CPU ARM9 (ou ARM7) executa a instrução que escreve `DMAxCNT` e dispara o DMA
- **THEN** o item traz `cpu` igual àquele core e `pc` igual ao **endereço da instrução do
  store** (o mesmo que o desassembler mostra naquele ponto), não o endereço seguinte
