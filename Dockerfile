#############################################
# Build stage
#############################################
FROM python:3.10-slim AS build

ARG APT_CACHE_ID=apt-cache-app
ARG UV_CACHE_ID=uv-cache-app

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /src

# Ставим только lock + project-метаданные
COPY pyproject.toml uv.lock ./

# Правильная установка зависимостей через uv.lock
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked,id=${APT_CACHE_ID} \
    --mount=type=cache,target=/root/.cache/uv,sharing=locked,id=${UV_CACHE_ID} \
    bash -euxo pipefail -c '\
      export DEBIAN_FRONTEND=noninteractive; \
      mkdir -p /var/cache/apt/archives/partial; \
      rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/cache/apt/archives/partial/lock; \
      for i in 1 2 3 4 5; do \
        apt-get -o Acquire::Retries=5 update && \
        apt-get -y -o Dpkg::Use-Pty=0 --no-install-recommends install \
          build-essential git cmake ninja-build pkg-config curl libopenblas-dev python3-dev && break || sleep 3; \
      done; \
      pip install --no-cache-dir "uv>=0.8"; \
      uv pip sync --system --no-cache pyproject.toml; \
      apt-get purge -y --auto-remove git cmake build-essential python3-dev ninja-build; \
      apt-get clean; rm -rf /var/lib/apt/lists/* \
    '

# Остальной исходный код
COPY . .

#############################################
# Runtime stage
#############################################
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    APP_MODULE=app.main:app \
    WEB_CONCURRENCY=1 \
    HEALTHCHECK_URL=http://127.0.0.1:8000/health

# В рантайм добавляем curl для healthcheck'ов из деплой-скрипта
RUN bash -euxo pipefail -c '\
      apt-get update && \
      apt-get install -y --no-install-recommends ca-certificates curl && \
      apt-get clean && rm -rf /var/lib/apt/lists/* \
    '

# Переносим установленный питон/пакеты и приложение
COPY --from=build /usr/local /usr/local
COPY --from=build /src /app

WORKDIR /app

# Healthcheck и старт-скрипт
COPY scripts/healthcheck.py /app/scripts/healthcheck.py
COPY scripts/start-web.sh   /app/scripts/start-web.sh
RUN chmod +x /app/scripts/start-web.sh

EXPOSE 8000

# Встроенный healthcheck на Python (без внешних утилит)
HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD python /app/scripts/healthcheck.py || exit 1

# Стартуем через скрипт (uvicorn + опции)
CMD ["/app/scripts/start-web.sh"]
