#!/usr/bin/env bash
#
# Deploy local: builda o emulador (da main dele) + sobe o MCP re-mcp como
# servidor de rede (streamable-http), para o agente conectar manualmente.
# O emulador NÃO é iniciado aqui (isso é do agente ou seu).
#
# Uso:
#   ./deploy.sh up      # derruba emulador, builda emulador + MCP, sobe o MCP
#   ./deploy.sh down    # derruba o MCP
#   ./deploy.sh logs    # segue os logs do MCP
#   ./deploy.sh ps      # status do MCP
#
# O `up` sempre parte das mains (nada de worktree/PR divergente):
#   MCP:      git fetch origin main        + switch main + pull --ff-only
#   emulador: git fetch origin <branch>    + switch <branch> + pull --ff-only + build
# (aborta se houver mudanças locais). O emulador é derrubado antes do build.
#
# O deploy é agnóstico à ROM: o MCP lê a ROM carregada no emulador pelo canal
# de controle (`rom.info`/`rom.read`), sem bind-mount nem caminho fixo.
#
# Variáveis (opcionais, com defaults):
#   MELONDS_REPO     checkout do emulador        (default: ../melonDS)
#   MELONDS_BRANCH   branch do emulador          (default: master)
#   BUILD_TYPE       tipo de build do emulador   (default: Release)
#   SKIP_EMULATOR_BUILD  =1 pula o build do emulador
#   MELONDS_DIR      dir do canal de controle    (default: ~/melonds)
#   OUT_DIR          dir de saída do MCP          (default: ~/re_mcp_out)
#   MCP_PORT         porta HTTP                   (default: 8765)
#
# Depois, aponte o cliente para:  http://127.0.0.1:${MCP_PORT}/mcp
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="$SCRIPT_DIR/mcp/docker-compose.yml"
[[ -f "$COMPOSE" ]] || { echo "não achei $COMPOSE" >&2; exit 1; }

: "${MCP_PORT:=8765}"
: "${MELONDS_REPO:=$SCRIPT_DIR/../melonDS}"
: "${MELONDS_BRANCH:=master}"
: "${BUILD_TYPE:=Release}"
export MCP_PORT

COMPOSE_ARGS=(-f "$COMPOSE")

sync_mcp() {
  echo ">> git (mcp): fetch + switch main + pull"
  git -C "$SCRIPT_DIR" fetch origin main
  git -C "$SCRIPT_DIR" switch main
  git -C "$SCRIPT_DIR" pull --ff-only origin main
}

build_emulator() {
  [[ -d "$MELONDS_REPO/.git" ]] || { echo "!! não achei o repo do emulador: $MELONDS_REPO" >&2; exit 1; }
  echo ">> emulador: derrubando instâncias"
  pkill -9 -x melonDS 2>/dev/null || true
  echo ">> git (emulador): fetch + switch $MELONDS_BRANCH + pull"
  git -C "$MELONDS_REPO" fetch origin "$MELONDS_BRANCH"
  git -C "$MELONDS_REPO" switch "$MELONDS_BRANCH"
  git -C "$MELONDS_REPO" pull --ff-only origin "$MELONDS_BRANCH"
  echo ">> build do emulador ($BUILD_TYPE, JIT off, GDB on)"
  cmake -S "$MELONDS_REPO" -B "$MELONDS_REPO/build" -G Ninja \
    -DENABLE_JIT=OFF \
    -DENABLE_GDBSTUB=ON \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    -DENABLE_LTO_RELEASE=OFF
  cmake --build "$MELONDS_REPO/build" -j"$(nproc)"
  echo ">> emulador: $MELONDS_REPO/build/melonDS (não iniciado)"
}

case "${1:-up}" in
  up)
    sync_mcp
    if [[ "${SKIP_EMULATOR_BUILD:-0}" != "1" ]]; then
      build_emulator
    fi
    docker compose "${COMPOSE_ARGS[@]}" up --build -d
    echo ">> re-mcp em http://127.0.0.1:${MCP_PORT}/mcp"
    ;;
  down) docker compose "${COMPOSE_ARGS[@]}" down ;;
  logs) docker compose "${COMPOSE_ARGS[@]}" logs -f --tail=100 ;;
  ps)   docker compose "${COMPOSE_ARGS[@]}" ps ;;
  *) echo "uso: $0 [up|down|logs|ps]" >&2; exit 2 ;;
esac
