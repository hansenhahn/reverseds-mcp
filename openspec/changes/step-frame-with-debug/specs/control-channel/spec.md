## REMOVED Requirements

### Requirement: Controle de execução

**Reason**: a parada/retomada deixa de ser um pause próprio do canal de controle — "parar/
rodar" passa a ser do **debugger** (halt / `continue`), e o avanço é `emu.step_frame`. Manter
dois "parado" conflitantes travava o debugger: com o emulador pausado, o stub gdb não era
servido, então o `debug_connect` não respondia.

**Migration**: use `emu.step_frame` para avançar quadros e o debugger (`debug_interrupt` para
parar, `debug_resume` para rodar).
