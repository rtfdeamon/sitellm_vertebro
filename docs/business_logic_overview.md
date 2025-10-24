# Business Logic Overview

This document summarizes the major subsystems exposed by the `sitellm_vertebro`
service after the recent refactorings. Each section highlights the main data
flows, storage dependencies, and FastAPI endpoints responsible for executing
business logic so the content can be converted to PDF or used for onboarding.

---

## 1. Authentication & Admin Guardrails
- **BasicAuthMiddleware** (`app.py`): protects `/admin` and `/api/v1/admin/**`
  routes.  
  - Validates against `ADMIN_USER`/`ADMIN_PASSWORD_DIGEST` or project-specific
    admin accounts stored in Mongo (`project.admin_password_hash`).  
  - Successful authentication stores an `AdminIdentity` on
    `request.state.admin`, driving project scoping for subsequent handlers.
- **Admin session endpoint** (`/api/v1/admin/session`): returns username,
  permissions, and allowed project set derived from the middleware identity.

---

## 2. LLM Interaction & Chat Flow
- **Endpoint**: `POST /api/v1/llm/ask` (see `api.py: ask_llm`).  
  - Builds conversation context by merging preset messages, prior chat history,
    and project prompt overrides.  
  - Maintains dialog turn limits (`_MAX_DIALOG_TURNS`, `_MAX_DIALOG_CHARS`);
    auto-summarizes history when exceeding thresholds.
  - Retrieves knowledge snippets via `_collect_knowledge_snippets`, which
    consults:
    - MongoDB QA pairs (`mongo_client.search_qa_pairs`).  
    - Qdrant hybrid search (`retrieval_search.hybrid_search`).  
    - Mongo document search (`mongo_client.search_documents` +
      GridFS content fetch).
  - **Reading mode**: automatically enabled if snippets include reading content
    from the knowledge base; attaches condensed previews through
    `ReadingService`.  
  - Integrations: attaches Bitrix/Mail "plan" instructions to the response
    metadata when the model suggests actions.
  - Caching: leverages Redis via `backend.cache` to memoize responses for the
    same session/prompt.

---

## 3. Knowledge Base Administration
Everything is encapsulated inside `KnowledgeAdminHandlers` (`app.py`).

- **Document management**  
  - `GET/POST /api/v1/admin/knowledge`: list/create text documents, queue auto
    descriptions (Celery) when metadata is missing.  
  - `PUT /api/v1/admin/knowledge/{file_id}`: updates, handles text/binary
    variants, regenerates summaries, reassigns projects, and syncs runner hubs
    (Telegram/Max/VK) when project definitions change.  
  - `DELETE /api/v1/admin/knowledge/{file_id}`: removes documents and triggers
    vector-store refresh in the worker.
  - Uploads (`POST /api/v1/admin/knowledge/upload`) store payloads in GridFS,
    set download URLs, and optionally trigger auto-description.
- **Maintenance operations**  
  - Deduplication (`POST /deduplicate`), vector rebuild (`POST /reindex`),
    project-wide purge (`DELETE /api/v1/admin/knowledge`).
- **Priority & knowledge services**  
  - `GET/POST /api/v1/admin/knowledge/priority`: configurable ordering for
    knowledge sources (`qa`, `qdrant`, `mongo`).  
  - Knowledge service status/update/run endpoints manage a background process
    that refreshes autosummaries; settings stored in Mongo (`app_settings`).
- **QA & unanswered flows**  
  - CRUD for FAQ pairs (`/api/v1/admin/knowledge/qa/...`).  
  - Unanswered question queue: list, clear, export, and stream as CSV.

---

## 4. Reading Experience
- **Service**: `ReadingService` (`app_modules/services/reading.py`).  
  - Normalizes reading pages (segments, images, HTML) with global character
    limits to keep widget payloads manageable.  
  - Builds previews linked from knowledge snippets; includes pagination metadata
    (`startOffset`, `initialIndex`, `has_more`).  
  - `GET /reading/pages`: exposed endpoint that delegates to `ReadingService`.
- **Crawler ingestion helpers**: `crawler.run_crawl.prepare_reading_material`
  and `chunk_reading_blocks` (covered by `tests/test_reading_mode.py`).

---

## 5. Voice Training Subsystem
`VoiceService` (`app_modules/services/voice.py`) consolidates the logic.

- **Sample lifecycle**  
  - `GET/POST/DELETE /voice/samples`: list existing samples, upload new audio
    (size/type validation), and remove entries. Stored in Mongo collections
    `voice_samples` and GridFS.
- **Training jobs**  
  - `GET /voice/jobs` & `/voice/status`: list or fetch the most recent job for
    a project.  
  - `POST /voice/train`: validates sample count, checks for existing jobs,
    requeues stale ones, and enqueues new training (Celery) or runs inline when
    queueing fails.  
  - Watchdog coroutine `_voice_job_watchdog` revives jobs stuck in `queued`.
- **Queue integration**: uses `worker.voice_train_model.delay`; falls back to
  inline simulation when Celery brokers are unavailable.

---

## 6. Crawler & Knowledge Harvesting
- **Service**: `CrawlerService` (`app_modules/services/crawler.py`).  
  - `POST /crawler/run`: spawns `crawler/run_crawl.py` as a subprocess with
    CLI parameters for depth, book scraping flags, and Mongo URI context.  
  - `GET /crawler/status`: merges Mongo crawler stats with runtime metrics
    (`core.status.status_dict`), adds human-readable notes.  
  - `POST /crawler/reset`, `/deduplicate`, `/stop`: maintenance endpoints to
    clean job queues, deduplicate recent URLs, or terminate the running
    crawler (PID file kill).

---

## 7. Backups & Disaster Recovery
- **Configuration endpoints** (`/api/v1/backup/settings`, `/status`): read/store
  backup schedules (hour/minute/timezone, Yandex Disk folder, optional token).
- **Operations**  
  - `POST /api/v1/backup/run`: runs backups via `worker.backup_execute`, with
    conflict detection when another job is active.  
  - `POST /api/v1/backup/restore`: initiates restore jobs, pulling artifacts
    from remote storage.  
  - Status endpoints serialize `BackupJob` models, showing history and active
    operations.

---

## 8. Feedback & User Support
- Centralized in `FeedbackHandlers` (created alongside reading refactor).  
  - `POST /api/v1/feedback`: stores feedback tasks (project, contact info,
    source) in Mongo.  
  - Admin list/update endpoints to review tasks, set status, and persist notes.
  - Status constraints enforced against `_FEEDBACK_STATUS_VALUES`.

---

## 9. Integrations: Bitrix & Mail
- **LLM pre-processing**: `_plan_bitrix_action` and `_plan_mail_action`
  evaluate user messages with LLM templates (`BITRIX_COMMAND_PROMPT`,
  `MAIL_COMMAND_PROMPT`).  
  - Extracts structured JSON actions (create task, send email, list inbox).  
  - Accepted plans stored in Redis (TTL set via `MAIL_PLAN_TTL`).
- **Confirmation flows**  
  - Bitrix confirm/cancel: `/api/v1/llm/bitrix/confirm` / `cancel`.  
  - Mail confirm/cancel: `/api/v1/llm/mail/confirm` / `cancel`.  
  - Persist results back into Mongo logs, optionally send HTTP requests or
    emails via connectors (`integrations.bitrix`, `integrations.mail`).

---

## 10. Observability & Operations
- **Metrics middleware** (`observability.metrics`): instrumented via Starlette
  middleware; `/metrics` endpoint is mounted separately.  
  - Response payloads leverage `collect_request_stats` to track request/latency.
- **Logging**: uses `structlog` (with stubbed fallback in tests).  
  - Admin logs endpoint (`/api/v1/admin/logs`) reads recent lines using
    `observability.logging.get_recent_logs`.
- **Health checks**  
  - `/healthz`: simple liveness.  
  - `/status`: aggregates redis/mongo/qdrant availability, last crawl stats,
    etc., using `core.status.status_dict`.

---

## 11. Worker & Async Tasks
- **Knowledge auto-description** (`knowledge/tasks.py`): Celery task that reads
  GridFS documents, uses LLM to generate summaries, and updates metadata
  (status, timestamps). Retries when the LLM cluster is unavailable.
- **Vector store refresh**: triggered via `loop.run_in_executor` when knowledge
  docs are created/updated/deleted to keep embeddings in sync (`worker.update_vector_store`).
- **Backup processing**: executed by worker queue invoked through API endpoints.

---

## 12. Configuration & Environment Dependencies
- MongoDB: central persistence layer for projects, documents, runner configs,
  backups, QA pairs, unanswered questions, voice jobs, and settings.
- Redis: caching responses, storing integration plans, and toggling features.  
- Qdrant: vector search for hybrid knowledge retrieval.  
- Celery workers: optional, provide asynchronous offline tasks (auto-describe,
  voice training, backup execution).
- External services: Bitrix 24 REST hooks, SMTP/IMAP mail connectors,
  Yandex Disk (or other storage) for backups, Telegram/Max/VK bot integrations
  through respective hubs.

---

### How to reuse this document
1. Save as Markdown (`docs/business_logic_overview.md`).  
2. Convert to PDF using `pandoc docs/business_logic_overview.md -o business_logic.pdf`
   or by importing into any Markdown-aware editor and exporting.
