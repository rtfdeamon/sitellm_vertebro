# SiteLLM Vertebro

SiteLLM Vertebro is an end-to-end platform for collecting domain knowledge,
embedding it into a vector store and serving grounded answers via a FastAPI
backend.  The stack bundles a crawler, embeddings worker, admin dashboard,
chat widget and optional Telegram bot, so that a single deployment can ingest
and serve information for multiple projects or domains.

> **Looking for a quick orientation?** Start with the architecture and
> subsystem reference in `docs/`:
> - `docs/architecture.rst`
> - `docs/components.rst`
> - `docs/workflows.rst`

---

## Feature Highlights

- **Multi-project knowledge bases** – isolate content, prompts and LLM models
  per project while sharing infrastructure.
- **Incremental crawling pipeline** – cleanses HTML/PDF content, stores it in
  Mongo/GridFS and refreshes embeddings only for new material.
- **Grounded chat responses** – hybrid retrieval mixes vector search with
  keyword signals and feeds curated excerpts into the LLM.
- **Operations dashboard** – monitor services, manage knowledge documents,
  inspect prompts/logs and control the Telegram bot from one UI.
- **Intelligent knowledge processor** – optional microservice refreshes
  embeddings automatically when the crawler queue stays idle.
- **Request analytics** – per-project request statistics are logged in Mongo;
  the admin panel shows daily activity for the last 14 days and allows
  exporting CSV reports for external analysis.
- **Composable deployment** – run locally with `uv` or spin up the full stack
  using Docker Compose (GPU settings included).

---

## Repository Layout

```
admin/          – operator dashboard (static HTML/JS)
api.py          – public API router (chat, crawler, knowledge)
app.py          – FastAPI application factory and lifespan hooks
backend/        – shared infrastructure (settings, LLM client, caching)
core/           – status aggregation and health checks
crawler/        – asynchronous site crawler and Celery tasks
docs/           – Sphinx documentation (architecture, workflows)
retrieval/      – hybrid search utilities and reranking pipeline
tg_bot/         – optional Telegram bot (Aiogram)
widget/         – embeddable chat widget (SSE stream)
worker.py       – Celery worker that maintains the vector store
```

Additional helper directories include `observability/` (logging + metrics),
`scripts/` (benchmarks, maintenance jobs) and platform-specific deployment
scripts under the repository root.

---

## Prerequisites

- MongoDB 5+ and Redis (or use the bundled Docker services)
- Python 3.9+ with [uv](https://github.com/astral-sh/uv)
- Build toolchain for llama.cpp (`cmake`, `gcc`/`clang`, OpenBLAS)
- Optional GPU acceleration: CUDA Toolkit or Vulkan for llama.cpp

Clone the repository and copy the environment template:

```bash
git clone https://github.com/rtfdeamon/sitellm_vertebro.git
cd sitellm_vertebro
cp .env.example .env
```

Populate the `.env` file with MongoDB and Redis credentials (required by the
app, worker and crawler).  Additional environment variables are documented in
`settings.py` and `backend/settings.py`.

---

## Local Development

Install project dependencies via `uv` (CUDA flags optional):

```bash
CMAKE_ARGS="-DGGML_CUDA=on -DGGML_BLAS=ON" uv sync
```

Spawn the API and Celery worker in separate terminals:

```bash
uvicorn app:app --reload
celery -A worker worker --beat
```

Open the admin dashboard at `http://localhost:18080/admin/` to create your
first project, configure the base prompt and trigger a crawl.

### Optional services

- **Telegram bot** – configure the token in the admin UI and start the bot via
  the "Telegram Bot" card.
- **Metrics** – Prometheus-compatible metrics are exposed at `/metrics` when
  the app runs under Uvicorn/Gunicorn.

---

## Docker Compose Stack

To run the complete stack with all dependencies (MongoDB, Redis, Qdrant,
Ollama/YaLLM, Celery worker and the API) execute:

```bash
docker compose up --build
```

Useful overrides:

- `compose.gpu.yaml` – enable GPU-backed inference.
- `docker-compose.override.windows.yml` – CPU/memory limits for Windows hosts.

> Tip: use `python3 scripts/update_versions.py --format shell` to bump the
> service-specific image versions before calling `docker compose build`. This
> keeps unchanged containers cached and mirrors the behaviour of the deploy
> scripts described below.

Knowledge base operations and the background service are documented in `docs/knowledge_service.md` and `docs/crawler_images.md`.

The helper script `./deploy_project.sh` automates environment generation,
tracks per-service image versions and rebuilds only the containers whose
sources changed before performing an initial crawl.  The PowerShell variant
`./deploy_project.ps1` provides the same behaviour on Windows.

---

## Knowledge Workflow

1. **Create a project** – provide a slug, optional display title and the
   system prompt the LLM should follow.  Every chat request logs a
   `project_prompt_attached` entry confirming the prompt is applied.
2. **Collect knowledge** – either upload documents via the admin UI or launch
   an automated crawl.  Crawled text is cleaned (navigation stripped, PDF
   spacing restored) before being stored in Mongo/GridFS.  When you upload
   binaries (PDF agreements, scans, licence photos) provide a short
   description – it is indexed for search and used as the caption when the
   chat widget or Telegram bot shares the attachment with users.
3. **Index embeddings** – the Celery worker tracks the latest document
   timestamp and incrementally updates the Redis vector store after each
   crawl or manual upload.
4. **Serve answers** – chat requests call `/api/v1/llm/ask` which retrieves
   hybrid search results, injects them into the prompt and streams the final
   answer to the widget/bot.
5. **Dynamic sites** – for SPA/JS-heavy pages export `CRAWL_JS_RENDER=1`
   (optionally tweak `CRAWL_JS_WAIT` and `CRAWL_JS_TIMEOUT`). The crawler will
   render pages with Playwright before extracting text; install Playwright and
   run `playwright install chromium` inside the container/venv beforehand.
6. **Page timeout** – each URL is processed at most `CRAWL_PAGE_TIMEOUT`
   seconds (defaults to 120 s) so slow resources do not stall the queue.

The "Logs" panel in the admin UI shows the full compiled prompt for each
request (`llm_prompt_compiled`), making it easy to audit which sources were
used.

---

## Testing

Run the unit test suite with:

```bash
python -m pytest
```

For lightweight load tests and latency measurements use:

```bash
python scripts/benchmark.py --requests 200 --concurrency 8
```

---

## Documentation

Build the Sphinx docs locally:

```bash
sphinx-build -b html docs build/docs
```

The generated site summarises architecture, components and operational
workflows.  Extend it with module-level autodoc if deeper API references are
required.

---

## Deployment Notes

- Automate rollouts with the instructions in `docs/deploy.md`.
- For one-off installations run `deploy_project.sh` (Linux/macOS) or
  `deploy_project.ps1` (Windows).  Both scripts produce `.env` backups and wait
  for the API health check before exiting.
- After deployment visit the admin dashboard, create a project and verify that
  the status cards report healthy Mongo/Redis/Qdrant connections.

---

## Support & Monitoring

- Health endpoints: `/health` (external dependencies) and `/healthz`
  (container liveness).
- Metrics: `/metrics` (Prometheus exposition).
- Logs: admin dashboard "Logs" card + container logs via Docker.

If you encounter issues, start by checking the crawler progress channel in
Redis (`crawler:events`) and the Celery worker logs for embedding status.
