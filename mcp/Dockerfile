# Imagem do MCP de engenharia reversa assistida.
#
# python:3.x-slim (glibc, wheels prontas) — evita o atrito do musl/Alpine.
# O backend de debug precisa do gdb-multiarch (pacote de sistema).
FROM python:3.14-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gdb-multiarch \
    && rm -rf /var/lib/apt/lists/*

# uv (gerenciador de dependências)
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

# O contêiner acessa:
#   - o canal de controle por bind-mount do socket Unix
#   - o stub GDB pela rede do host (network_mode: host)
ENV RE_MCP_CONTROL_SOCKET=/run/melonds/control.sock

ENTRYPOINT ["uv", "run", "--no-dev", "python", "-m", "re_mcp"]
