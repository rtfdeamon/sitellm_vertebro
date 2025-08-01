# YaLLM

This project exposes a simple API backed by Yandex GPT models using the
`llama-cpp-python` runtime. Documents are stored in MongoDB/GridFS and their
embeddings are indexed in Redis.

Before running the application, copy the provided `.env.example` file to `.env`
and fill in the connection parameters for MongoDB and Redis. The compose file
expects at least `MONGO_USERNAME` and `MONGO_PASSWORD` to be set.

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

Alternatively you can start the whole stack using Docker Compose:

```bash
docker compose up --build
```
The compose file uses MongoDB `7` and Qdrant `v1.9` images.

## Testing

Run unit tests with:

```bash
pytest -q
```

## Configuration

Key settings are loaded from environment variables or ``.env``:

| Variable | Default | Description |
|----------|---------|-------------|
| ``LLM_URL`` | ``http://localhost:8000`` | vLLM HTTP endpoint used by ``backend.llm_client`` |
| ``EMB_MODEL_NAME`` | ``sentence-transformers/sbert_large_nlu_ru`` | Embedding model name for the vector store |
| ``RERANK_MODEL_NAME`` | ``sbert_cross_ru`` | Cross-encoder used for reranking search results |
| ``REDIS_URL`` | ``redis://localhost:6379/0`` | Redis instance storing cached responses and vectors |

MongoDB and Redis specific variables also use prefixes ``MONGO_`` and
``REDIS_`` as documented in ``settings.py``.

## Telegram Bot Usage

The optional Telegram bot can be started with Docker Compose. Set the
following variables in ``.env``:

* ``TG_BOT_TOKEN`` – bot token from BotFather.
* ``TG_API_URL`` – URL of the backend chat API (usually ``http://api:8000/api/chat``).
* ``SUPPORT_GROUP_ID`` – identifier of the operator group.

Then run:

```bash
docker compose up -d telegram
```

The bot supports the ``/operator`` command to switch a user into operator mode
and ``/end`` to return to the LLM.

## Project Structure

```
backend/      - application logic and FastAPI router
retrieval/    - search utilities and embedding models
tg_bot/       - optional Telegram bot implementation
observability/ - Prometheus metrics setup
scripts/      - helper scripts like benchmark and crawler
``` 
