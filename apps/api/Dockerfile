# syntax=docker/dockerfile:1

# ---- build: install deps via uv ----
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# deps dulu dari lockfile → layer ke-cache kalau lock tak berubah
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime: image final, kecil & non-root ----
FROM python:3.12-slim AS runtime
RUN useradd -m -u 1000 app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
COPY --chown=app:app entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
# Folder cache harus ADA dan dimiliki app SEBELUM volume dipasang. Kalau belum ada,
# Docker membuatnya sebagai root dan fastembed gagal mengunduh model (Permission denied).
RUN mkdir -p /app/.model-cache && chown app:app /app/.model-cache
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 MODEL_CACHE_DIR=/app/.model-cache
USER app
EXPOSE 8010
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "job_match_api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8010"]
