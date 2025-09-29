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
* ``GET /api/v1/reading/pages`` – prepared book-reading pages with LLM-written
  teasers and linked media for the widget’s scrolling reader.
* ``POST /api/v1/llm/mail/confirm`` / ``/mail/cancel`` – approve or discard
  email actions drafted by the Telegram bot's mail connector.

Crawler pipeline
----------------

Located in ``crawler/`` and ``backend/crawler_reporting.py``.

* ``run_crawl.py`` – async BFS crawler with PDF/HTML extraction, text
  cleaning, queue deduplication and Mongo/GridFS writes.  Before workers start
  fetching pages the pending queue is normalised to ensure duplicate URLs are
  removed, keeping the crawl budget focused on unique content.  When the
  ``collect_books`` flag is enabled the crawler also strips common
  header/footer fragments, stores the full page text, and generates 1.5k
  character reading segments with short LLM teasers in the
  ``reading_pages`` collection so the widget can stream a book-like
  experience.
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
  knowledge browser, logs, status cards, and integration management.  Ships
  with a 10-language UI selector (English, Español, Deutsch, Français,
  Italiano, Português, Русский, 中文, 日本語, العربية) so deployments can
  localise the interface without additional builds.  The crawler launch form
  now exposes a “book reading” toggle that enables the new ingestion mode, and
  the project form includes a mail connector card for configuring IMAP/SMTP
  endpoints plus a default signature for outbound messages.  A separate toggle
  lets operators surface knowledge-source links in end-user replies when
  needed.
* ``widget/`` – embeddable chat widget that streams token responses from
  ``/api/v1/llm/chat``.
* ``widget/widget-loader.js`` – drop-in script that renders the widget as a
  floating bubble or inline card on third-party sites.
* ``widget/voice-avatar.js`` – animated, voice-enabled avatar that uses the
  Web Speech API plus SSE for conversations without embedding the full widget.
  When book-reading mode is active it fetches ``/api/v1/reading/pages`` and
  renders both a scrollable preview panel and a full-screen "book" reader with
  page navigation, summaries, illustrations, and per-page source links.
* ``tg_bot/`` – Telegram bot built on Aiogram; started and monitored through
  the admin panel.  It manages confirmation flows for attachment delivery,
  Bitrix actions, and the mail connector to keep potentially destructive
  operations under operator control.

Testing and tooling
-------------------

* ``tests/`` – unit tests for crawler behaviour and API glue code.
* ``scripts/`` – operational helpers (benchmarks, maintenance jobs).
* ``observability/`` – logging configuration (in-memory buffer retains seven
  days of entries for the admin log viewer) and Prometheus metrics middleware.
* ``deploy_project.sh`` / ``deploy_project.ps1`` – automated one-shot
  installation scripts for Linux/macOS and Windows.
