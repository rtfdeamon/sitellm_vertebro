### ---------- Build stage ----------
FROM python:3.10-slim AS build

# Кэши ускоряют Linux/arm64 сборку на Docker Desktop (Apple Silicon)
ARG APT_CACHE_ID=apt-cache
ARG UV_CACHE_ID=uv-cache
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
ARG CMAKE_ARGS
ARG LLAMA_CPP_PYTHON_BUILD

# Ускорители и надёжность сетевых скачиваний для uv/pip во время сборки
ENV UV_HTTP_TIMEOUT=180 \
    UV_HTTP_MAX_RETRIES=5
ENV PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL} \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    CMAKE_ARGS=${CMAKE_ARGS} \
    LLAMA_CPP_PYTHON_BUILD=${LLAMA_CPP_PYTHON_BUILD}

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
COPY pyproject.toml ./

# Устанавливаем зависимости по lock-файлу (детерминированно и кэшируемо)
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked,id=${UV_CACHE_ID} \
    bash -euxo pipefail -c '\
      # Явно используем PyPI для установки uv, чтобы не зависеть от PIP_* переменных
      pip install --no-cache-dir -i https://pypi.org/simple "uv>=0.8"; \
      # Устанавливаем зависимости из pyproject.toml; uv будет кэшировать резолв
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
        libopenblas0-pthread \
        curl ca-certificates; \
      apt-get clean; \
      rm -rf /var/lib/apt/lists/* \
    '

COPY --from=build /usr/local /usr/local
COPY --from=build /src /app
RUN python -m compileall -q /app
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

# Лёгкая проверка живости API (без внешних зависимостей)
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=10 \
  CMD curl -fsS http://127.0.0.1:${PORT}/healthz || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
