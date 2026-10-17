#!/usr/bin/env bash
#
# Smoke test do GDB stub do melonDS: sobe o emulador, conecta no ARM9,
# lê registradores/memória e desassembla. Não-interativo.
#
# Uso:  ./smoke-test.sh "/caminho/jogo.nds"
#
set -uo pipefail

ROM="${1:? uso: smoke-test.sh <rom.nds>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MELONDS_DIR="${MELONDS_DIR:-$SCRIPT_DIR/../melonDS}"
MEL="$MELONDS_DIR/build/melonDS"
LOG=/tmp/melonds-smoke.log

[[ -x "$MEL" ]] || { echo "não achei $MEL (defina MELONDS_DIR)" >&2; exit 1; }
[[ -f "$ROM" ]]  || { echo "ROM não encontrada: $ROM" >&2; exit 1; }

pkill -9 -x melonDS 2>/dev/null
sleep 0.5
rm -f "$LOG"

setsid env QT_QPA_PLATFORM=offscreen LIBGL_ALWAYS_SOFTWARE=1 \
    "$MEL" "$ROM" >"$LOG" 2>&1 &
MPID=$!
echo "melonDS pid=$MPID; aguardando boot..."
sleep 6

if ! kill -0 "$MPID" 2>/dev/null; then
    echo "melonDS morreu no boot. Log:"; sed -n '1,40p' "$LOG"; exit 1
fi

echo ">> conectando no ARM9 (:3333)"
timeout -k 5 25 gdb-multiarch -q --nx -batch \
    -ex "set debuginfod enabled off" \
    -ex "set confirm off" \
    -ex "set architecture arm" \
    -ex "target remote 127.0.0.1:3333" \
    -ex "info registers pc sp lr" \
    -ex "x/6i \$pc" \
    -ex "x/4xw 0x02000000" \
    -ex "detach" 2>&1

kill -9 "$MPID" 2>/dev/null
pkill -9 -x melonDS 2>/dev/null

echo
echo "=== linhas do stub no log ==="
grep -iE "\[GDB\]" "$LOG" | head -8
