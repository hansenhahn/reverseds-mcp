#!/usr/bin/env bash
#
# Sobe o melonDS COM INTERFACE GRAFICA, com o canal de controle ativo, para
# testar a injecao de input "de verdade": voce joga na janela e o agente injeta
# junto (o input e mesclado).
#
# Uso:  ./nds-control.sh "/caminho/jogo.nds"
#
set -uo pipefail

ROM="${1:? uso: nds-control.sh <rom.nds>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MELONDS_DIR="${MELONDS_DIR:-$SCRIPT_DIR/../melonDS}"
MEL="$MELONDS_DIR/build/melonDS"
SOCK="/tmp/melonds-control.sock"
CFG="${XDG_CONFIG_HOME:-$HOME/.config}/melonDS/melonDS.toml"
LOG=/tmp/melonds-gui.log

[[ -x "$MEL" ]] || { echo "não achei $MEL (defina MELONDS_DIR)" >&2; exit 1; }
[[ -f "$ROM" ]] || { echo "ROM não encontrada: $ROM" >&2; exit 1; }

# garante o canal de controle habilitado no config
mkdir -p "$(dirname "$CFG")"
if ! grep -q '^\[Control\]' "$CFG" 2>/dev/null; then
    printf '\n[Control]\nEnabled = true\nSocket = "%s"\n' "$SOCK" >> "$CFG"
    echo ">> adicionado [Control] em $CFG"
elif ! grep -A3 '^\[Control\]' "$CFG" | grep -q 'Enabled = true'; then
    echo "!! habilite 'Control.Enabled = true' em $CFG" >&2
fi

pkill -9 -x melonDS 2>/dev/null
sleep 0.5
rm -f "$SOCK"

echo ">> subindo melonDS (GUI) com: $ROM"
setsid "$MEL" "$ROM" >"$LOG" 2>&1 </dev/null &
disown 2>/dev/null || true

# espera o socket do canal aparecer
for _ in $(seq 1 40); do
    [[ -S "$SOCK" ]] && break
    sleep 0.5
done
if [[ ! -S "$SOCK" ]]; then
    echo "!! o socket $SOCK não apareceu — veja $LOG" >&2
    exit 1
fi

echo ">> canal de controle ativo em $SOCK"
echo ">> demo: injetando A por 1s e depois um toque..."

CLIENT="python3 $SCRIPT_DIR/control-client.py"
$CLIENT "$SOCK" input.key '{"mask": 1022}' >/dev/null   # A
sleep 1
$CLIENT "$SOCK" input.release >/dev/null
$CLIENT "$SOCK" input.touch '{"x": 128, "y": 96}' >/dev/null
sleep 1
$CLIENT "$SOCK" input.release >/dev/null

echo ">> demo: capturando as duas telas (PNG)..."
( cd "$SCRIPT_DIR" && python3 control-client.py "$SOCK" screen.capture '{"screens":"both","format":"rgba8"}' )

cat <<EOF

Pronto. O melonDS está rodando — jogue na janela normalmente.
Para injetar input pelo canal de controle:
  $CLIENT $SOCK input.key '{"mask": 1022}'      # A pressionado
  $CLIENT $SOCK input.release                    # solta tudo
  $CLIENT $SOCK input.touch '{"x":128,"y":96}'   # toque
  $CLIENT $SOCK                                  # modo interativo

Máscara de teclas (active-low, 1=solto / 0=pressionado; 0xFFF = nada):
  A=bit0 B=bit1 Select=bit2 Start=bit3 Right=bit4 Left=bit5
  Up=bit6 Down=bit7 R=bit8 L=bit9 X=bit10 Y=bit11

Capturar a tela (salva capture_0.png / capture_1.png em $SCRIPT_DIR):
  $CLIENT $SOCK screen.capture '{"screens":"both","format":"rgba8"}'
Streaming a 1 fps por 10s (salva cada quadro):
  $CLIENT $SOCK screen.capture '{"screens":"top","every_ms":1000,"duration_ms":10000}'
EOF
