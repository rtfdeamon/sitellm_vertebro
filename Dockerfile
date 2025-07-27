# Base image includes `uv` package manager for deterministic installs
FROM ghcr.io/astral-sh/uv:debian-slim

WORKDIR app
# Copy application source
COPY . .

# Install build dependencies required by llama-cpp-python
RUN apt update && apt install g++ gcc libopenblas-dev pkg-config -y
# Configure CMake to build CUDA and BLAS support
ENV CMAKE_ARGS "-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS"
# Install Python dependencies using uv
RUN uv sync


# The FastAPI application listens on port 8000
EXPOSE 8000

# Start the API with uvicorn
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0"]