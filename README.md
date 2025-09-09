# YaLLM

This project exposes a simple API backed by Yandex GPT models using the
`llama-cpp-python` runtime. Documents are stored in MongoDB/GridFS and their
embeddings are indexed in Redis.

Before running the application copy `.env.example` to `.env` and fill in the
connection parameters for MongoDB and Redis. The compose file expects at least
`MONGO_USERNAME` and `MONGO_PASSWORD` to be set.

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

## One-shot deployment

For an automated setup on Linux or macOS the repository ships a helper
script:

```bash
./deploy_project.sh
```

The script asks for your domain name, writes a `.env` file, builds the Docker
images sequentially, waits for the API to become healthy from inside the
`app` container and then launches an initial crawl.  The crawl start URL
defaults to `https://<DOMAIN>` but can be overridden by setting
`CRAWL_START_URL` before running the script.  Run with `--yes` to skip
interactive prompts.

## Auto-deploy (push to main)

For automatic rollout to a target server on each push to `main`, see
`docs/deploy.md`. It describes required GitHub Action secrets and a
non-interactive server-side script used by the workflow.

## Testing

Run unit tests with:

```bash
pytest -q
```

## Documentation

Build the HTML documentation with:

```bash
sphinx-build -b html docs build/docs
```

Inline code is documented with comprehensive docstrings across modules; the
Sphinx configuration is set to include undoc-members so new symbols will be
picked up automatically.

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

* ``BOT_TOKEN`` – bot token from BotFather.
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

## Windows quickstart

> Требуется: **Docker Desktop**, **Git for Windows**, **PowerShell 7+**.  
> Рекомендуется включённый WSL2 backend в Docker Desktop.

1. Клонировать репозиторий и перейти в папку проекта.
2. (Опционально) отредактировать `.env.example`.
3. Запустить:

```powershell
.\deploy_project.ps1
```

Скрипт:
- проверит наличие инструментов;
- создаст/обновит `.env` (при необходимости сгенерирует пароль для Mongo);
- сохранит бэкап env в `deploy-backups\<timestamp>-windows.zip`;
\- соберёт образы последовательно (без `--no-parallel`);
\- поднимет `docker compose` со слабыми лимитами CPU/RAM через `docker-compose.override.windows.yml`;
\- дождётся готовности API по `http://localhost:${APP_PORT:-8000}/healthz`.

### Нагрузка на слабых машинах
По умолчанию в Windows-оверрайде заданы щадящие параметры:

```bash
SERVICE_CPUS=1.0
SERVICE_MEM_LIMIT=1g
UVICORN_WORKERS=1
CELERY_WORKERS=1
```

Меняйте значения через переменные в `.env` или в окружении, не правя YAML.

### Первичный crawl
Если хотите сразу запустить первичный обход сайта, передайте URL:

```powershell
.\deploy_project.ps1 -CrawlUrl "https://example.com"
```

> Если в проекте используется другой CLI-модуль для crawl — поправьте команду внутри скрипта (поиск `sitellm_vertebro.crawl`).

Минимальный краулер `crawler/run_crawl.py` загружает `robots.txt` и обходит
только разрешённые страницы. При наличии `sitemap.xml` очередь стартовых URL
расширяется адресами из карты сайта. Явный URL карты можно указать через
`--sitemap-url`, а флаг `--ignore-robots` отключит проверку `robots.txt`.

### Вопросы к модели по HTTP
После запуска можно обращаться к API из PowerShell:

```powershell
$port = ${env:APP_PORT} ; if(-not $port){ $port = 8000 }
Invoke-RestMethod -Uri "http://localhost:$port/api/chat" -Method POST `
  -ContentType "application/json" `
  -Body (@{messages=@(@{role="user";content="Привет!"})} | ConvertTo-Json -Depth 5)
```

Маршрут `/api/chat` приведён как пример — используйте фактические эндпойнты проекта.

## Web Chat Widget

After the stack is running the application serves a small widget at
``/widget/``. Open [http://localhost:8000/widget/](http://localhost:8000/widget/)
in a browser and type a question to see the model's answer streamed live.

To reuse the widget in another site copy ``widget/index.html`` and adjust the
``EventSource`` URL to your deployment.
