## ADDED Requirements

### Requirement: Header completo da ROM

O adapter de cartucho SHALL expor o header completo (0x200 bytes) da ROM carregada, com
título, gamecode, makercode, unit/region/version/autostart, ARM9/ARM7 (offset/entry/RAM/size),
FNT/FAT, tabelas y9, ícone, CRCs e tamanho usado. Bytes ausentes SHALL ser tratados como zero.

#### Scenario: Header completo
- **WHEN** o header é lido de uma ROM válida
- **THEN** os campos de identidade, ARM9/ARM7, FNT/FAT, overlays e CRCs são preenchidos

#### Scenario: Header curto
- **WHEN** o header tem menos de 0x200 bytes mas pelo menos 0x60
- **THEN** os campos ausentes são zero e o parse não falha
