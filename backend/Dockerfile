FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --system --uid 10001 --home-dir /data jacquard && mkdir -p /data && chown jacquard /data
USER jacquard
ENV JACQUARD_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8000

# L'API n'est jamais exposée directement : seul Caddy, sur le réseau interne, lui
# parle. On peut donc faire confiance à son en-tête X-Forwarded-For.
CMD ["sh", "-c", "jacquard db upgrade && exec uvicorn jacquard.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*' --timeout-graceful-shutdown 5 --workers ${JACQUARD_WORKERS:-2}"]
