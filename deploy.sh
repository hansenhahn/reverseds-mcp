#!/usr/bin/env bash
#
# Deploy local do MCP re-mcp como servidor de rede (streamable-http), para o
# agente conectar manualmente (o cliente NÃO sobe o contêiner).
#
# Uso:
#   ./deploy.sh up      # (fetch + switch main + pull) build + sobe em background
#   ./deploy.sh down    # derruba
#   ./deploy.sh logs    # segue os logs
#   ./deploy.sh ps      # status
#
# O `up` sempre parte da main: faz `git fetch origin main`, `git switch main` e
# `git pull --ff-only` antes do build (aborta se houver mudanças locais).
#
# O deploy é AGNÓSTICO à ROM. Enquanto o emulador não for a fonte da verdade da
# ROM, inclua o override com MCP_COMPOSE_EXTRA (lista separada por ':'):
#   ROM_PATH="/caminho/jogo.nds" \
#     MCP_COMPOSE_EXTRA="mcp/docker-compose.rom.yml" ./deploy.sh up
#
# Variáveis (opcionais, com defaults):
#   MELONDS_DIR  dir do canal de controle  (default: ~/melonds)
#   OUT_DIR      dir de saída do MCP        (default: ~/re_mcp_out)
#   MCP_PORT     porta HTTP                 (default: 8765)
#   MCP_COMPOSE_EXTRA  overrides do compose (separados por ':')
#
# Depois, aponte o cliente para:  http://127.0.0.1:${MCP_PORT}/mcp
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="$SCRIPT_DIR/mcp/docker-compose.yml"
[[ -f "$COMPOSE" ]] || { echo "não achei $COMPOSE" >&2; exit 1; }

: "${MCP_PORT:=8765}"
export MCP_PORT

COMPOSE_ARGS=(-f "$COMPOSE")
if [[ -n "${MCP_COMPOSE_EXTRA:-}" ]]; then
  IFS=':' read -r -a extras <<< "$MCP_COMPOSE_EXTRA"
  for extra in "${extras[@]}"; do
    [[ -f "$extra" ]] || extra="$SCRIPT_DIR/$extra"
    COMPOSE_ARGS+=(-f "$extra")
  done
fi

case "${1:-up}" in
  up)
    echo ">> git: garantindo a main"
    git -C "$SCRIPT_DIR" fetch origin main
    git -C "$SCRIPT_DIR" switch main
    git -C "$SCRIPT_DIR" pull --ff-only origin main
    docker compose "${COMPOSE_ARGS[@]}" up --build -d
    echo ">> re-mcp em http://127.0.0.1:${MCP_PORT}/mcp"
    ;;
  down) docker compose "${COMPOSE_ARGS[@]}" down ;;
  logs) docker compose "${COMPOSE_ARGS[@]}" logs -f --tail=100 ;;
  ps)   docker compose "${COMPOSE_ARGS[@]}" ps ;;
  *) echo "uso: $0 [up|down|logs|ps]" >&2; exit 2 ;;
esac
