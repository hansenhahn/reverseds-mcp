#!/usr/bin/env bash
#
# Teste ponta-a-ponta do WATCHPOINT DE HARDWARE (PR #2424).
# Arma um write watchpoint e confirma que o stub usa hardware (Z2, sem
# single-step de software) e que o emulador para na escrita.
#
# Uso:
#   ./wp-hw.sh "/caminho/jogo.nds"            # vigia o endereço de $sp
#   ./wp-hw.sh "/caminho/jogo.nds" 0x02000000 # vigia um endereço fixo
#
set -uo pipefail

ROM="${1:? uso: wp-hw.sh <rom.nds> [endereco_hex]}"
ADDR="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MELONDS_DIR="${MELONDS_DIR:-$SCRIPT_DIR/../melonDS}"
MEL="$MELONDS_DIR/build/melonDS"
LOG=/tmp/melonds-wp.log

[[ -x "$MEL" ]] || { echo "não achei $MEL (defina MELONDS_DIR)" >&2; exit 1; }
[[ -f "$ROM" ]]  || { echo "ROM não encontrada: $ROM" >&2; exit 1; }

if [[ -n "$ADDR" ]]; then
    TARGET="*(unsigned int*)${ADDR}"
else
    TARGET='*(unsigned int*)$sp'
fi

pkill -9 -x melonDS 2>/dev/null
sleep 0.5
rm -f "$LOG"

setsid env QT_QPA_PLATFORM=offscreen LIBGL_ALWAYS_SOFTWARE=1 \
    "$MEL" "$ROM" >"$LOG" 2>&1 &
MPID=$!
echo "melonDS pid=$MPID; aguardando boot..."
sleep 6

echo ">> watchpoint de hardware em: $TARGET"
timeout -k 5 40 gdb-multiarch -q --nx -batch \
    -ex "set debuginfod enabled off" \
    -ex "set confirm off" \
    -ex "set pagination off" \
    -ex "set architecture arm" \
    -ex "target remote 127.0.0.1:3333" \
    -ex "set remote hardware-watchpoint-limit 4" \
    -ex "watch $TARGET" \
    -ex "info breakpoints" \
    -ex "continue" \
    -ex 'printf "PAROU em pc=%#x\n", $pc' \
    -ex "detach" 2>&1

kill -9 "$MPID" 2>/dev/null
pkill -9 -x melonDS 2>/dev/null

echo
echo "=== pacotes Z2 enviados ao stub (>=1 = watchpoint de HW ativo) ==="
grep -c "Z2" "$LOG" || true
echo "=== single-steps no log (0 = hardware, não emulação por SW) ==="
grep -c "single-step" "$LOG" || true
