### ---------- Build stage ----------
FROM python:3.10-slim AS build

# Кэши ускоряют Linux/arm64 сборку на Docker Desktop (Apple Silicon)
ARG APT_CACHE_ID=apt-cache
ARG UV_CACHE_ID=uv-cache

# Базовые пакеты для сборки wheels (компилятор и т.д.)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked,id=${APT_CACHE_ID} \
    bash -euxo pipefail -c '\
      export DEBIAN_FRONTEND=noninteractive; \
      apt-get update; \
      apt-get install -y --no-install-recommends \
        build-essential git cmake ninja-build pkg-config curl \
        libopenblas-dev python3-dev; \
      rm -rf /var/lib/apt/lists/* \
    '

WORKDIR /src
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости из pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked,id=${UV_CACHE_ID} \
    bash -euxo pipefail -c '\
      pip install --no-cache-dir "uv>=0.8"; \
      uv pip install --system --no-cache --requirements pyproject.toml; \
    '

# Остальной исходный код
COPY . .

### ---------- Runtime stage ----------
FROM python:3.10-slim AS runtime

# Минимально необходимые рантайм-зависимости
# - libopenblas: so-шки для numpy/scipy
# - build-essential и др. — чтобы при необходимости собирать колёса
# - curl/ca-certificates: для healthcheck и любых http-пингов
ARG APT_CACHE_ID=apt-cache-runtime
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked,id=${APT_CACHE_ID} \
    bash -euxo pipefail -c '\
      export DEBIAN_FRONTEND=noninteractive; \
      apt-get update; \
      apt-get install -y --no-install-recommends \
        libopenblas0-pthread libopenblas-dev \
        build-essential cmake ninja-build pkg-config \
        curl ca-certificates; \
      apt-get clean; \
      rm -rf /var/lib/apt/lists/* \
    '

COPY --from=build /usr/local /usr/local
COPY --from=build /src /app
WORKDIR /app

# Мягкие настройки для слабых CPU/ноутбуков
ENV PYTHONUNBUFFERED=1 \
    UVICORN_WORKERS=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_MAX_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    PYTHONPATH=/app \
    PORT=8000

# Неблокирующий healthcheck: сначала пытаемся /healthz, потом /health, иначе TCP-порт
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=10 \
  CMD bash -lc '\
    (curl -fsS http://127.0.0.1:${PORT}/healthz || \
     curl -fsS http://127.0.0.1:${PORT}/health  || \
     python - <<PY \
import os, socket, sys; \
 p=int(os.environ.get("PORT","8000")); \
 s=socket.socket(); \
 s.settimeout(2); \
 ok=False \
 try: s.connect(("127.0.0.1",p)); ok=True \
 except Exception: pass \
 finally: s.close() \
 sys.exit(0 if ok else 1) \
PY \
    ) >/dev/null 2>&1 || exit 1'

## Команда старта берётся из docker-compose; здесь ничего не переопределяем.
