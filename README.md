# YaLLM

This project exposes a simple API backed by Yandex GPT models using the
`llama-cpp-python` runtime. Documents are stored in MongoDB/GridFS and their
embeddings are indexed in Redis.

## Requirements
- gcc or clang
- cmake
- openblas
- [CUDA](https://developer.nvidia.com/cuda-toolkit)

Python dependencies are managed with [uv](https://github.com/astral-sh/uv).
To install them run:

```bash
CMAKE_ARGS="-DGGML_CUDA=on -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS -DGGML_VULKAN=on" uv sync
```

## Running
Start the FastAPI application using:

```bash
uvicorn app:app --reload
```

A Celery worker can be started with:

```bash
celery -A worker worker --beat
```
