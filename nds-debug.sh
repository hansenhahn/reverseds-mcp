#!/usr/bin/env bash
#
# Sobe o melonDS (headless) e abre o gdb-multiarch já conectado ao ARM9,
# com watchpoints de hardware habilitados.
#
# Uso:  ./nds-debug.sh "/caminho/jogo.nds" [arm9|arm7]
#
# Resolve o melonDS pelo irmão ../melonDS, ou defina MELONDS_DIR.
#
set -uo pipefail

ROM="${1:? uso: nds-debug.sh <rom.nds> [arm9|arm7]}"
CORE="${2:-arm9}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MELONDS_DIR="${MELONDS_DIR:-$SCRIPT_DIR/../melonDS}"
MEL="$MELONDS_DIR/build/melonDS"
LOG=/tmp/melonds.log

case "$CORE" in
    arm9|9) PORT=3333 ;;
    arm7|7) PORT=3334 ;;
    *) echo "core inválido: $CORE (use arm9 ou arm7)" >&2; exit 2 ;;
esac

[[ -x "$MEL" ]] || { echo "não achei $MEL (defina MELONDS_DIR)" >&2; exit 1; }
[[ -f "$ROM" ]]  || { echo "ROM não encontrada: $ROM" >&2; exit 1; }

pkill -9 -x melonDS 2>/dev/null
sleep 0.5

setsid env QT_QPA_PLATFORM=offscreen LIBGL_ALWAYS_SOFTWARE=1 \
    "$MEL" "$ROM" >"$LOG" 2>&1 &
echo "melonDS subindo (pid $!, log em $LOG) — core $CORE na porta $PORT"
sleep 6

exec gdb-multiarch -q \
    -ex "set debuginfod enabled off" \
    -ex "set pagination off" \
    -ex "set confirm off" \
    -ex "set architecture arm" \
    -ex "set remotetimeout 20" \
    -ex "target remote 127.0.0.1:$PORT" \
    -ex "set remote hardware-watchpoint-limit 4"
