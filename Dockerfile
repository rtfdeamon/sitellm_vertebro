# Build stage: installs dependencies into the system environment.
FROM python:3.10-slim AS build

WORKDIR /src
COPY pyproject.toml uv.lock ./

# Increase timeout for large wheel downloads.
ENV UV_HTTP_TIMEOUT=600

# Cache apt/uv downloads, remove stale locks, install build deps and sync Python deps.
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/root/.cache/uv \
    rm -f /var/lib/apt/lists/lock \
          /var/cache/apt/archives/lock \
          /var/cache/apt/archives/partial/lock && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential git cmake ninja-build pkg-config curl libopenblas-dev python3-dev && \
    pip install --no-cache-dir 'uv>=0.8' && \
    uv pip sync --no-cache && \
    apt-get purge -y --auto-remove git cmake build-essential python3-dev ninja-build && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . .

# Runtime stage: copy dependencies and application source.
FROM python:3.10-slim

COPY --from=build /usr/local /usr/local
COPY --from=build /src /app

WORKDIR /app
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0"]
