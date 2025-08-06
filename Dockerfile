# Dockerfile for building the FastAPI application and Celery services.
#
# Dependencies are installed in a separate build stage using ``uv`` so the
# final runtime image remains lean.
# Build stage
FROM python:3.10-slim AS build
WORKDIR /app
COPY pyproject.toml uv.lock ./
# Increase UV_HTTP_TIMEOUT to accommodate large wheel downloads such as scikit-learn.
ENV UV_SYSTEM_PYTHON=1 UV_CACHE_DIR=/tmp/uv UV_HTTP_TIMEOUT=600
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        # gcc, g++, make, libc headers
        build-essential \
        # needed by llama-cpp-python’s CMake scripts
        git \
        # recent CMake for scikit-build-core
        cmake \
        ninja-build \
        pkg-config \
        curl \
        libopenblas-dev \
        # Python headers for native wheels
        python3-dev \
    && export PIP_EXTRA_INDEX_URL=https://abetlen.github.io/llama-cpp-python/whl/cpu \
    && export FORCE_CMAKE=1 CMAKE_ARGS="-DLLAMA_ARM_DOTPROD=OFF -DLLAMA_ARM_FMA=OFF -DLLAMA_ARM_FP16=OFF" \
    && pip install --no-cache-dir uv \
    && uv sync --no-cache \
    # optional: slim the final image
    && apt-get purge -y --auto-remove git cmake build-essential python3-dev ninja-build \
    && rm -rf /var/lib/apt/lists/*

# make sure CMake sees the compilers
ENV CC=/usr/bin/gcc
ENV CXX=/usr/bin/g++
COPY . .

# Runtime stage
FROM python:3.10-slim
WORKDIR /app
COPY --from=build /usr/local /usr/local
COPY --from=build /app /app
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0"]
