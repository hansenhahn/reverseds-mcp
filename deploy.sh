#!/usr/bin/env bash
#
# Deploy local do MCP re-mcp como servidor de rede (streamable-http), para o
# agente conectar manualmente (o cliente NÃO sobe o contêiner).
#
# Uso:
#   ./deploy.sh up      # build + sobe em background (padrão)
#   ./deploy.sh down    # derruba
#   ./deploy.sh logs    # segue os logs
#   ./deploy.sh ps      # status
#
# Variáveis (opcionais, com defaults):
#   MELONDS_DIR  dir do canal de controle  (default: ~/melonds)
#   ROM_PATH     caminho da ROM            (default: /dev/null)
#   OUT_DIR      dir de saída do MCP        (default: ~/re_mcp_out)
#   MCP_PORT     porta HTTP                 (default: 8765)
#
# Depois, aponte o cliente para:  http://127.0.0.1:${MCP_PORT}/mcp
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="$SCRIPT_DIR/mcp/docker-compose.yml"
[[ -f "$COMPOSE" ]] || { echo "não achei $COMPOSE" >&2; exit 1; }

: "${MCP_PORT:=8765}"
export MCP_PORT

case "${1:-up}" in
  up)
    docker compose -f "$COMPOSE" up --build -d
    echo ">> re-mcp em http://127.0.0.1:${MCP_PORT}/mcp"
    ;;
  down) docker compose -f "$COMPOSE" down ;;
  logs) docker compose -f "$COMPOSE" logs -f --tail=100 ;;
  ps)   docker compose -f "$COMPOSE" ps ;;
  *) echo "uso: $0 [up|down|logs|ps]" >&2; exit 2 ;;
esac
