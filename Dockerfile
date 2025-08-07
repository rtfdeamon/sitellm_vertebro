# Build stage: installs dependencies into a virtual environment.
FROM python:3.10-slim AS build

WORKDIR /src
COPY pyproject.toml uv.lock ./

# Increase timeout for large wheel downloads.
ENV UV_HTTP_TIMEOUT=600

# Cache apt packages between builds.
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential git cmake ninja-build pkg-config curl libopenblas-dev python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Cache pip/uv downloads.
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir uv
RUN --mount=type=cache,target=/root/.cache/uv uv sync --venv /opt/venv --no-cache

COPY . .

# Runtime stage: copy only venv and application source.
FROM python:3.10-slim
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=build /opt/venv /opt/venv
COPY --from=build /src /app

WORKDIR /app
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0"]
