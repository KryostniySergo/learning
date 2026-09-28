# syntax=docker/dockerfile:1
FROM python:3.13-slim

# uv — тот же менеджер пакетов, что и в разработке
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    HF_HOME=/opt/hf

WORKDIR /app

# Пользователь и его папки — заранее, чтобы модель сразу скачалась от его имени
RUN useradd --create-home --uid 1000 appuser \
 && mkdir -p /opt/hf /app/data/chroma /app/data/raw \
 && chown -R appuser:appuser /opt/hf /app/data

# 1. Зависимости — отдельным слоем: он пересобирается, только когда меняется uv.lock
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 2. Модель — в образ, от имени appuser (без последующего chown)
USER appuser
ARG EMBEDDING_MODEL=intfloat/multilingual-e5-small
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"
ENV HF_HUB_OFFLINE=1 \
    APP_EMBEDDING_MODEL=${EMBEDDING_MODEL}

# 3. Код — последним: он меняется чаще всего
COPY app ./app
COPY scripts ./scripts
COPY eval ./eval

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]