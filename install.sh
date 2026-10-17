#!/usr/bin/env bash
#
# Instalação completa do ambiente de depuração GDB para NDS:
#   dependências -> fork/clone -> branch com PR #2424 -> build (JIT off/GDB on)
#   -> config do stub -> (opcional) pwndbg
#
# Uso:
#   ./install.sh                      # instala tudo
#   INSTALL_DIR=~/melonDS ./install.sh
#   ./install.sh --skip-deps --no-pwndbg
#   ./install.sh --pwndbg --skip-clone
#
# Variáveis: GITHUB_USER, FORK_REPO, UPSTREAM_REPO, PR_NUMBER, BRANCH,
#            INSTALL_DIR, BUILD_TYPE, ARM9_PORT, ARM7_PORT, PWNDBG_DIR
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

GITHUB_USER="${GITHUB_USER:-hansenhahn}"
FORK_REPO="${FORK_REPO:-$GITHUB_USER/melonDS}"
UPSTREAM_REPO="${UPSTREAM_REPO:-melonDS-emu/melonDS}"
PR_NUMBER="${PR_NUMBER:-2424}"
BRANCH="${BRANCH:-dev/gdb-watchpoints}"
INSTALL_DIR="${INSTALL_DIR:-$SCRIPT_DIR/../melonDS}"
BUILD_TYPE="${BUILD_TYPE:-Release}"
ARM9_PORT="${ARM9_PORT:-3333}"
ARM7_PORT="${ARM7_PORT:-3334}"
PWNDBG_DIR="${PWNDBG_DIR:-$HOME/Work/pwndbg}"

DO_DEPS=1
DO_CLONE=1
DO_BUILD=1
DO_CONFIG=1
DO_PWNDBG="ask"   # yes | no | ask

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!! %s\033[0m\n' "$*"; }

usage() {
    cat <<'EOF'
Instalação completa do ambiente de depuração GDB para NDS:
  dependências -> fork/clone -> branch com PR #2424 -> build (JIT off/GDB on)
  -> config do stub -> (opcional) pwndbg

Uso:
  ./install.sh                      # instala tudo
  INSTALL_DIR=~/melonDS ./install.sh
  ./install.sh --skip-deps --no-pwndbg
  ./install.sh --pwndbg --skip-clone

Flags: --skip-deps --skip-clone --skip-build --skip-config --pwndbg --no-pwndbg

Variáveis: GITHUB_USER, FORK_REPO, UPSTREAM_REPO, PR_NUMBER, BRANCH,
           INSTALL_DIR, BUILD_TYPE, ARM9_PORT, ARM7_PORT, PWNDBG_DIR
EOF
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --skip-deps)  DO_DEPS=0 ;;
            --skip-clone) DO_CLONE=0 ;;
            --skip-build) DO_BUILD=0 ;;
            --skip-config) DO_CONFIG=0 ;;
            --pwndbg)     DO_PWNDBG=yes ;;
            --no-pwndbg)  DO_PWNDBG=no ;;
            -h|--help)    usage ;;
            *) warn "opção desconhecida: $1"; usage ;;
        esac
        shift
    done
}

install_deps() {
    say "Dependências de sistema"
    if ! command -v apt-get >/dev/null 2>&1; then
        warn "apt-get não encontrado. Instale manualmente: cmake ninja qt6-base-dev"
        warn "qt6-base-private-dev qt6-multimedia-dev qt6-svg-dev qt6-wayland libsdl2-dev"
        warn "libarchive-dev libenet-dev libzstd-dev libfaad-dev libcurl4-gnutls-dev"
        warn "libpcap0.8-dev extra-cmake-modules gdb-multiarch"
        return
    fi
    local SUDO=""
    [[ $EUID -ne 0 ]] && SUDO="sudo"
    $SUDO apt-get update
    $SUDO apt-get install -y \
        cmake ninja-build extra-cmake-modules libcurl4-gnutls-dev \
        libpcap0.8-dev libsdl2-dev libarchive-dev libenet-dev libzstd-dev libfaad-dev \
        qt6-base-dev qt6-base-private-dev qt6-multimedia-dev qt6-svg-dev qt6-wayland \
        gdb-multiarch
}

clone_repo() {
    say "Repositório do melonDS em: $INSTALL_DIR"
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        echo "já existe, pulando clone."
        return
    fi
    mkdir -p "$(dirname "$INSTALL_DIR")"

    # Garante que o fork existe (se gh estiver disponível e autenticado).
    if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
        gh repo view "$FORK_REPO" >/dev/null 2>&1 || \
            gh repo fork "$UPSTREAM_REPO" --clone=false --remote=false >/dev/null 2>&1 || true
    fi

    if ! git clone "https://github.com/$FORK_REPO.git" "$INSTALL_DIR" 2>/dev/null; then
        warn "clone do fork falhou; clonando direto o upstream."
        git clone "https://github.com/$UPSTREAM_REPO.git" "$INSTALL_DIR"
    fi
}

prepare_branch() {
    say "Branch '$BRANCH' = upstream + PR #$PR_NUMBER"
    cd "$INSTALL_DIR"
    git remote get-url upstream >/dev/null 2>&1 || \
        git remote add upstream "https://github.com/$UPSTREAM_REPO.git"
    git fetch upstream --prune
    git checkout -q master
    git merge --ff-only upstream/master || warn "master local divergiu do upstream."
    git fetch upstream "pull/$PR_NUMBER/head:refs/heads/$BRANCH" --force
    git checkout "$BRANCH"
    git merge upstream/master --no-edit || warn "merge com upstream/master colidiu; resolva à mão."
    echo "branch atual: $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse --short HEAD)"
}

build() {
    say "Build (ENABLE_JIT=OFF, ENABLE_GDBSTUB=ON, $BUILD_TYPE)"
    cd "$INSTALL_DIR"
    cmake -B build -G Ninja \
        -DENABLE_JIT=OFF \
        -DENABLE_GDBSTUB=ON \
        -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
        -DENABLE_LTO_RELEASE=OFF
    cmake --build build -j"$(nproc)"
    [[ -x build/melonDS ]] && echo "OK: $INSTALL_DIR/build/melonDS"
}

write_config() {
    say "Config do GDB stub"
    local cfgdir="${XDG_CONFIG_HOME:-$HOME/.config}/melonDS"
    local cfg="$cfgdir/melonDS.toml"
    mkdir -p "$cfgdir"

    local block
    block="$(cat <<EOF
[Instance0.Gdb]
Enabled = true

[Instance0.Gdb.ARM9]
Port = $ARM9_PORT
BreakOnStartup = true

[Instance0.Gdb.ARM7]
Port = $ARM7_PORT
BreakOnStartup = false
EOF
)"

    if [[ -f "$cfg" ]]; then
        warn "já existe $cfg — garanta (sem duplicar seções) o seguinte:"
        printf '%s\n' "$block"
        return
    fi
    { echo "[Gdb]"; echo "Enabled = true"; echo; printf '%s\n' "$block"; } > "$cfg"
    echo "escrito: $cfg"
}

install_pwndbg() {
    say "pwndbg (opcional)"
    if [[ -d "$PWNDBG_DIR/.venv" ]]; then
        echo "já instalado em $PWNDBG_DIR"
        return
    fi
    git clone --depth 1 https://github.com/pwndbg/pwndbg.git "$PWNDBG_DIR"
    (
        cd "$PWNDBG_DIR"
        python3 -m venv .venv
        # shellcheck disable=SC1091
        source .venv/bin/activate
        pip install -U pip uv
        uv sync --no-install-project --group build
        uv sync --no-build-isolation-package pwndbg
    )
    echo "carregue com: gdb-multiarch -ex \"source $PWNDBG_DIR/gdbinit.py\""
}

main() {
    parse_args "$@"
    say "Instalação do ambiente de debug NDS (melonDS + PR #$PR_NUMBER)"
    echo "  INSTALL_DIR = $INSTALL_DIR"
    echo "  FORK        = $FORK_REPO"
    echo "  BRANCH      = $BRANCH"

    [[ $DO_DEPS  -eq 1 ]] && install_deps
    [[ $DO_CLONE -eq 1 ]] && { clone_repo; prepare_branch; }
    [[ $DO_BUILD -eq 1 ]] && build
    [[ $DO_CONFIG -eq 1 ]] && write_config

    if [[ "$DO_PWNDBG" == "ask" ]]; then
        read -r -p "Instalar pwndbg (melhora a UX do gdb)? [s/N] " a || a=""
        [[ "$a" =~ ^[sSyY]$ ]] && DO_PWNDBG=yes || DO_PWNDBG=no
    fi
    [[ "$DO_PWNDBG" == "yes" ]] && install_pwndbg

    say "Pronto!"
    cat <<EOF
Próximos passos:
  1) Rode:   $SCRIPT_DIR/nds-debug.sh "/caminho/jogo.nds"     # abre o gdb já conectado
  2) Teste:  $SCRIPT_DIR/smoke-test.sh "/caminho/jogo.nds"    # checa stub + watchpoint HW
  3) Guia completo: $SCRIPT_DIR/melonds-gdb-debugging.md
EOF
}

main "$@"
