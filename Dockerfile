# Build stage: installs dependencies into the system environment.
FROM python:3.10-slim AS build

WORKDIR /src
COPY pyproject.toml uv.lock ./

# Increase timeout for large wheel downloads.
ENV UV_HTTP_TIMEOUT=600

# Allow configuring cache IDs for parallel builds.
ARG APT_CACHE_ID=apt-cache-app
ARG UV_CACHE_ID=uv-cache-app

# Cache apt/uv downloads, remove stale locks, install build deps and sync Python deps.
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
      uv pip sync --no-cache; \
      apt-get purge -y --auto-remove git cmake build-essential python3-dev ninja-build; \
      apt-get clean; rm -rf /var/lib/apt/lists/* \
    '

COPY . .

# Runtime stage: copy dependencies and application source.
FROM python:3.10-slim

COPY --from=build /usr/local /usr/local
COPY --from=build /src /app

WORKDIR /app
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0"]
