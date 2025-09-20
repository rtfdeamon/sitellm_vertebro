=====================
System Architecture
=====================

The platform combines a FastAPI control plane, asynchronous crawling
pipeline, vector search stack, and multiple user interfaces.  The following
diagram describes the flow of data between the subsystems:

.. list-table:: Runtime data flow
   :header-rows: 1

   * - Stage
     - Description
   * - 1. Content acquisition
     - ``crawler/run_crawl.py`` traverses a seed URL breadth-first, extracts
       readable text, normalises it (PDF post-processing included) and stores
       documents in MongoDB/GridFS.  Progress is tracked in Redis so the
       admin dashboard can report queue state in real time.
   * - 2. Embedding & indexing
     - ``worker.py`` subscribes to Celery tasks and performs incremental
       updates of the Redis vector store using YaLLM embeddings.  A watermark
       timestamp ensures only fresh documents are re-embedded after crawls.
   * - 3. Retrieval & ranking
     - ``retrieval/search.py`` combines dense (Redis) and sparse search
       results, performs optional reranking, and returns knowledge snippets to
       the application layer.
   * - 4. Application services
     - ``app.py`` wires the FastAPI app, health checks, admin API, and
       lifecycle hooks.  ``api.py`` exposes public chat/knowledge endpoints
       consumed by the widgets and automation scripts.
   * - 5. Interfaces
     - ``admin/`` hosts the operations dashboard, ``widget/`` provides an
       embeddable chat client, and ``tg_bot/`` implements the optional
       Telegram bot.

Key external dependencies
-------------------------

The default docker-compose stack provisions everything needed to run the
system end-to-end:

* **MongoDB + GridFS** – durable storage for crawled artefacts.
* **Redis** – caching layer and vector store (via ``langchain_redis``).
* **Qdrant** (optional) – alternative vector database via ``retrieval``.
* **YaLLM / Ollama / llama.cpp** – large language model runtime accessed
  through ``backend.llm_client``.
* **Celery + Redis broker** – background workers for embeddings and reports.

Configuration surface
---------------------

The settings hierarchy is encapsulated in ``settings.py`` and ``backend/settings``.
Environment variables follow the component prefixes:

* ``MONGO_*`` – credentials, database, collection names.
* ``REDIS_*`` / ``REDIS_URL`` – caching/vector store connection details.
* ``CELERY_*`` – broker/result URLs for the worker.
* ``PROJECT_NAME`` / ``DOMAIN`` – default project slug when no explicit
  domain is provided in requests.

The admin UI persists per-project overrides (LLM model, base prompt) in the
``projects`` collection.  Runtime toggles, such as the Telegram token, live in
``app_settings``.
