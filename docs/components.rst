=====================
Subsystem Reference
=====================

API services
------------

``app.py`` initialises the FastAPI application, handles lifespan management
(Mongo clients, Redis vectors, metrics), and mounts the admin/widget static
sites.  Two routers define the public API surface:

* ``api.py`` – LLM chat endpoints, knowledge management helpers, crawler
  controls.  Attaches the project-specific system prompt before each
  generation and logs compiled prompts for observability.
* ``backend/`` – shared infrastructure (LLM client, settings helpers,
  caching decorators) imported by the routers.

Important endpoints:

* ``POST /api/v1/llm/ask`` – chat completion with knowledge grounding.
* ``GET /api/v1/crawler/status`` – aggregated crawler/DB metrics for the UI.
* ``POST /api/v1/admin/knowledge`` – upsert textual documents into MongoDB.
* ``POST /api/v1/admin/projects`` – manage per-domain configuration, including
  the initial system prompt used by the model.

Crawler pipeline
----------------

Located in ``crawler/`` and ``backend/crawler_reporting.py``.

* ``run_crawl.py`` – async BFS crawler with PDF/HTML extraction, text
  cleaning, queue deduplication and Mongo/GridFS writes.  Before workers
  start fetching pages the pending queue is normalised to ensure duplicate
  URLs are removed, keeping the crawl budget focused on unique content.
* ``tasks.py`` – Celery entry point that runs ``run_crawl`` and, upon
  completion, triggers ``worker.update_vector_store`` to synchronise the
  embeddings.
* ``backend/crawler_reporting.py`` – publishes progress snapshots to Redis
  hashes and pub/sub channels for the admin UI.

Worker and embeddings
---------------------

``worker.py`` configures Celery, initialises embeddings, and exposes two
tasks:

* ``update_vector_store`` – incremental refresh with watermark tracking.
* ``status.report`` – periodic logging of queue and database statistics.

Vector parsing uses ``vectors.py`` (Redis vector store wrapper) and
``yallm.py`` for embeddings model selection.

Retrieval layer
---------------

The ``retrieval/`` package provides hybrid search utilities that combine
vector and keyword features:

* ``search.py`` – entry point returning the scored snippets consumed by the
  API.
* ``rerank.py`` (if configured) – optional cross-encoder reranker.
* ``cache.py`` – Redis-backed memoisation helpers for expensive generation or
  rewrite steps.

User interfaces
---------------

* ``admin/`` – operations console with project switcher, crawler controls,
  knowledge browser, logs, and status cards.  Ships with a 10-language UI
  selector (English, Español, Deutsch, Français, Italiano, Português,
  Русский, 中文, 日本語, العربية) so deployments can localise the interface
  without additional builds.
* ``widget/`` – embeddable chat widget that streams token responses from
  ``/api/v1/llm/chat``.
* ``tg_bot/`` – Telegram bot built on Aiogram; started and monitored through
  the admin panel.

Testing and tooling
-------------------

* ``tests/`` – unit tests for crawler behaviour and API glue code.
* ``scripts/`` – operational helpers (benchmarks, maintenance jobs).
* ``observability/`` – logging configuration and Prometheus metrics middleware.
* ``deploy_project.sh`` / ``deploy_project.ps1`` – automated one-shot
  installation scripts for Linux/macOS and Windows.
