=====================
System Architecture
=====================

SiteLLM Vertebro unifies content ingestion, retrieval-augmented
conversation, and operator tooling.  The platform centres on a FastAPI
application that orchestrates crawling, knowledge indexing, LLM inference,
and multi-channel delivery.

Platform overview
-----------------

* ``app.py`` exposes HTTP APIs, serves the admin SPA and chat widget, and
  manages shared resources (Mongo clients, Redis caches, metrics).
* ``worker.py`` hosts the Celery worker responsible for vector embeddings,
  maintenance tasks, and background export jobs.
* ``crawler/run_crawl.py`` provides the asynchronous crawler that collects
  source material and normalises HTML/PDF content before persistence.
* ``knowledge_service/`` contains an optional microservice for automated
  document summarisation and enrichment tasks.
* ``admin/`` and ``widget/`` deliver browser-based UIs for operators and end
  users, while ``tg_bot/``, ``max_bot/`` and ``vk_bot/`` integrate external
  messengers.

Runtime topology
----------------

The default docker-compose stack launches all services required for local or
single-node deployments.  The interactions between key processes are rendered
with Graphviz for clarity:

.. graphviz::
   :name: runtime-topology
   :align: center

   digraph runtime {
       rankdir=LR;
       node [shape=box, style="rounded", fontname="Helvetica"];

       BrowserUIs [label="Browser UIs\n(admin/widget)"];
       FastAPIApp [label="FastAPI app\n(app.py & api.py)"];
       Redis [label="Redis\n(cache + vectors)"];
       Mongo [label="MongoDB\n+ GridFS"];
       Qdrant [label="Qdrant\n(optional)"];
       Worker [label="Celery worker\n(worker.py)"];
       Crawler [label="Crawler\n(run_crawl.py)"];
       Bots [label="Messaging bots\n(tg/max/vk)"];
       LLM [label="LLM runtimes\n(Ollama, YaLLM, llama.cpp)"];

       BrowserUIs -> FastAPIApp [label="HTTP / SSE"];
       FastAPIApp -> BrowserUIs [label="SSE"];
       Bots -> FastAPIApp [label="REST"];
       FastAPIApp -> Bots [label="callbacks"];

       FastAPIApp -> Redis [label="vectors"];
       Redis -> FastAPIApp [label="cache"];
       FastAPIApp -> Mongo [label="metadata"];
       Mongo -> FastAPIApp;
       FastAPIApp -> Qdrant [label="ANN queries"];
       Qdrant -> FastAPIApp;

       FastAPIApp -> Worker [label="Celery tasks"];
       Worker -> FastAPIApp [label="status"];
       Worker -> Redis [label="embeddings"];
       Worker -> Mongo [label="documents"];

       FastAPIApp -> Crawler [label="job config"];
       Crawler -> Mongo [label="documents"];
       Crawler -> Redis [label="progress"];

       FastAPIApp -> LLM [label="prompts"];
       LLM -> FastAPIApp [label="tokens"];
   }

Core components
----------------

.. list-table:: Deployment artefacts
   :header-rows: 1

   * - Component
     - Description
   * - FastAPI application
     - ``app.py`` wires routers from ``api.py``, mounts static assets, sets up
       health checks, and initialises shared clients (Mongo, Redis, Qdrant).
   * - API router
     - ``api.py`` exposes public endpoints: ``/api/v1/llm/ask`` for chat,
       ``/api/v1/crawler/*`` for crawl orchestration, and admin knowledge
       management APIs.
   * - Worker
     - ``worker.py`` boots Celery, registers periodic tasks, applies
       embedding updates via ``vectors.py`` and orchestrates knowledge refresh
       jobs.
   * - Crawler
     - ``crawler/run_crawl.py`` fetches pages with optional Playwright
       rendering, deduplicates queues, extracts readable text, and streams
       progress to Redis for the admin dashboard.
   * - Admin SPA
     - ``admin/index.html`` is a static dashboard that calls admin APIs using
       Basic authentication stored in browser session storage.
   * - Widget
     - ``widget/index.html`` provides the embeddable chat client that streams
       model responses over Server-Sent Events and prompts for admin
       credentials when invoking privileged operations.
   * - Messaging bots
     - ``tg_bot/``, ``max_bot/`` and ``vk_bot/`` wrap project-specific tokens
       and forward conversations through the same LLM pipeline.

Conversation flow
-----------------

1. A client (widget, bot, custom integration) issues ``POST /api/v1/llm/ask``
   with optional project scope and attachment references.
2. ``api.py`` normalises the project, builds or reuses a session identifier,
   and retrieves recent dialogue turns plus system presets from Mongo.
3. ``retrieval/search.py`` executes a hybrid search using Redis vectors,
   Qdrant (if enabled), and keyword heuristics, returning scored snippets.
4. ``backend.llm_client`` forwards the compiled prompt to the configured LLM
   runtime (Ollama/YaLLM/llama.cpp).  Streaming chunks are proxied back to the
   caller via SSE.
5. Responses, attachments, and analytics events are persisted in Mongo for
   auditability and follow-up workflows (statistics export, prompts log).

Mail connector workflow
-----------------------

The Telegram bot now drives a dedicated email connector that keeps the
knowledge base lean while automating mailbox tasks:

1. A user asks the bot to perform a mail action ("отправь врачу письмо", "что
   пришло на почту за час").
2. ``api.py`` calls ``_plan_mail_action`` which prompts the LLM with
   ``MAIL_COMMAND_PROMPT``.  Depending on intent it returns either a
   ``send_email`` payload or a ``list_inbox`` request.
3. For send operations the plan is stored in Redis (key ``mail:plan:<id>``)
   and surfaced to the user for confirmation.  Once the operator replies
   "да", ``/api/v1/llm/mail/confirm`` retrieves the plan, appends the project
   signature if requested, and relays the message through
   ``integrations.mail.send_mail`` using the project's IMAP/SMTP credentials.
4. Read-only queries call ``fetch_recent_messages`` which executes a
   best-effort IMAP ``SEARCH`` followed by lightweight header fetches.  The
   resulting summary is injected into the knowledge snippets so the LLM can
   reason on the up-to-date mailbox state.

Typical scenarios include:

* **Triage queue** – operators ask "что нового по почте" to read the latest
  unread threads without leaving Telegram, then follow up with "ответь, что
  запись подтверждена" to send templated confirmations.
* **Escalations** – users forward internal context ("перешли стенограмму
  доктору Иванову") and the connector drafts an email which can be checked
  and approved inline.
* **Scheduled follow-ups** – conversational timers ("напомни завтра и
  отправь письмо с инструкцией") combine the existing tasking flow with mail
  delivery so customers receive contextual instructions after interacting
  with the bot.

Knowledge ingestion pipeline
-----------------------------

1. Operators upload files via the admin UI or schedule a crawl through
   ``/api/v1/admin/knowledge`` endpoints.
2. ``crawler/run_crawl.py`` resolves the backlog, normalises URLs, renders
   dynamic pages if Playwright is enabled, and stores documents in MongoDB and
   GridFS.
3. Upon completion, the API enqueues a Celery task handled by ``worker.py``.
   The worker loads fresh documents, generates embeddings using YaLLM models,
   and updates Redis or Qdrant while maintaining watermarks to avoid
   reprocessing unchanged content.
4. Optional summarisation jobs in ``knowledge_service/`` enrich metadata used
   by search results and UI previews.

Storage and infrastructure
---------------------------

* **MongoDB + GridFS** store canonical documents, chat transcripts, and
  project configuration.  Collections are configurable via
  ``settings.MongoSettings``; schedule regular ``mongodump`` backups or run a
  replica set so the worker can index from secondaries while the primary
  keeps serving writes.  Per-request analytics form a rolling three-day queue
  backed by a TTL index, keeping export data fresh without unbounded growth.
* **Redis** fulfils multiple roles: caching, vector storage (through
  ``vectors.py``), crawl state, and Celery broker/result backend.  Enable AOF
  persistence for durability and configure separate logical databases when
  splitting cache traffic from Celery metadata.
* **Qdrant** integrates through ``retrieval/search.py`` as an alternative
  vector database when deployments require dedicated ANN storage.  Horizontal
  scaling is achieved by sharding on Qdrant collections while keeping Redis
  as the low-latency fallback.
* **File system** assets (admin/widget static files, uploaded blobs) are
  served by the FastAPI app via ``StaticFiles`` mounts; front them with a CDN
  or reverse proxy cache when hosting large document previews.
* **LLM backends** are abstracted behind ``backend.llm_client``.  The default
  configuration targets Ollama, but YaLLM and llama.cpp binaries can be
  swapped in without changing the API surface; production roll-outs typically
  run the runtime on a dedicated node and point ``llm_url`` at the managed
  endpoint.

Authentication and security
---------------------------

* Admin endpoints ``/admin`` and ``/api/v1/admin/*`` are protected by
  ``BasicAuthMiddleware`` in ``app.py``.  Browser clients cache credentials in
  session storage and prompt operators through ``requestAdminAuth`` helpers in
  ``admin/index.html`` and ``widget/index.html`` when a 401 is returned.
  Moving to SSO or signed cookies involves replacing that helper and swapping
  the middleware for a JWT or OAuth-aware implementation.
* Public chat endpoints are unauthenticated by default.  Deployments can
  front them with reverse-proxy auth (e.g. API gateways) when needed.
* Optional model-serving microservices (``backend/model_service.py``) accept
  bearer or ``X-API-Key`` tokens to restrict inference access.
* Sensitive configuration (database passwords, API keys, OAuth tokens) is
  sourced from environment variables via ``settings.py`` and never baked into
  the repository.

Observability
-------------

* ``observability/logging.py`` configures structlog-based JSON logs.  Admin
  operators can fetch recent events through ``/api/v1/admin/logs`` for UI
  inspection; notable records include ``llm_prompt_compiled`` and
  ``project_prompt_attached`` for audit trails.
* ``observability/metrics.py`` exposes Prometheus-compatible metrics at
  ``/metrics``; middleware is registered in ``app.py``.  The defaults include
  ``request_count`` (method/path labels), ``latency_ms``, and ``error_count``
  so dashboards can track p95 latency and failure spikes.
* Background status snapshots (crawler progress, worker health) are persisted
  in Redis ``crawler:progress:*`` hashes and the ``crawler:events`` pub/sub
  channel, allowing the dashboard and external monitors to stay in sync.

Deployment modes
----------------

* **Single-node / local development** – run ``uvicorn app:app --reload`` and
  ``celery -A worker worker --beat`` with local Mongo/Redis.  Static assets are
  served directly by the FastAPI process.
* **Docker Compose** – ``compose.yaml`` brings up MongoDB, Redis, Qdrant,
  Ollama, the API, worker, crawler, and auxiliary services.  GPU acceleration
  can be toggled via ``compose.gpu.yaml``.  Windows hosts rely on
  ``docker-compose.override.windows.yml`` for conservative resource limits.
* **Custom orchestration** – deployments can split the API, worker, crawler,
  and optional microservices into separate pods/VMs.  Shared state is limited
  to MongoDB, Redis, and the configured LLM runtime.

Configuration surface
---------------------

The settings layer is implemented with Pydantic models in ``settings.py`` and
``backend/settings.py``.  Notable groups:

* ``MONGO_*`` – connection parameters, collection names, and authentication
  database.
* ``REDIS_*`` / ``CELERY_*`` – broker, result backend, and TLS flags.
* ``MODEL_API_KEY`` – optional bearer or ``X-API-Key`` credential enforced by
  ``backend/model_service.py``.
* ``PROJECT_NAME`` / ``DOMAIN`` – default project scope for public requests.
* ``ADMIN_USERNAME`` / ``ADMIN_PASSWORD`` – hash-based credentials consumed by
  ``BasicAuthMiddleware``.
* ``MONGO_VOICE_SAMPLES`` / ``MONGO_VOICE_JOBS`` and related ``VOICE_*``
  limits – enable the admin console to accept voice training uploads and queue
  fine-tuning jobs for the animated avatar.

Extensibility points
--------------------

* Retrieval can be customised by overriding ``retrieval.search.hybrid_search``
  or plugging a different reranker via ``retrieval.rerank.rerank``.
* Messaging adapters inherit common helper patterns (token validation,
  webhook handling) and can be extended to new channels under
  ``integrations/`` by reusing ``backend.llm_client.generate``.
* The admin UI fetch layer centralises credential prompts, making it possible
  to add SSO or alternative auth by replacing ``requestAdminAuth`` in
  ``admin/index.html`` and ``widget/index.html``.
* Background jobs registered in ``worker.py`` can integrate additional
  post-processing (for example analytics export or nightly document
  summarisation) without touching the request path; extend
  ``worker.app.tasks`` to wire new periodic tasks.

Example: registering a custom retriever that enriches the hybrid search with
domain-specific heuristics::

   from retrieval import search

   def custom_hybrid_search(query: str, k: int = 10):
       docs = search.hybrid_search(query, k=k)
       return [doc for doc in docs if doc.payload.get("trust") != "low"]

   search.hybrid_search = custom_hybrid_search
