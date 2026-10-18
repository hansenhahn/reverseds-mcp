#!/usr/bin/env bash
#
# Smoke test local (determinístico) do re-mcp + melonDS.
#
# Sobe o melonDS headless e roda os casos contra o MESMO MCP (a partir do fonte,
# via stdio). Não usa Docker. Sai com código != 0 se algum caso falhar.
#
# Uso:
#   ./smoke/run-smoke.sh "/caminho/jogo.nds"          # todos os casos
#   ./smoke/run-smoke.sh "/caminho/jogo.nds" --only gdb
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROM="${1:?uso: run-smoke.sh <rom.nds> [opções do runner]}"
shift || true

echo ">> smoke: re-mcp + melonDS"
echo ">> repo: $REPO_ROOT"
cd "$REPO_ROOT"
exec uv run --project mcp python -m smoke --rom "$ROM" "$@"
