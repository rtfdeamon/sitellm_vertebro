# Build stage
FROM python:3.10-slim AS build
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \        # gcc, g++, make, libc headers
        git \                    # needed by llama-cpp-python’s CMake scripts
        cmake \                  # ensures a recent CMake
        pkg-config \
        curl \
        libopenblas-dev \
        python3-dev \            # Python headers for any native wheels
    && pip install --no-cache-dir uv \
    && uv sync \
    # optional: slim the final image
    && apt-get purge -y --auto-remove git cmake build-essential python3-dev \
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
