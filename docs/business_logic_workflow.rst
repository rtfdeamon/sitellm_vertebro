========================================
Business Logic Workflow & Verification
========================================

This document consolidates a detailed review of the SiteLLM Vertebro business
logic, identifies how each subsystem collaborates during critical workflows,
and lists the validations that keep data consistent.  It supplements
``architecture.rst`` by focusing on process-level behaviour rather than the
deployment topology.

.. contents::
   :depth: 2
   :local:

Actors & responsibilities
-------------------------

.. list-table::
   :header-rows: 1

   * - Actor / Service
     - Role in the workflow
     - Primary modules
   * - Operators (admin UI)
     - Configure projects, launch crawls, upload QA data, monitor analytics
     - ``admin/js/*.js``, ``api.py`` (admin routers)
   * - End users (widget / bots)
     - Ask questions, receive answers/voice replies
     - ``widget/``, ``tg_bot/``, ``voice/router.py``
   * - FastAPI application
     - Entry point for HTTP/WebSocket traffic, orchestrates use cases
     - ``app.py``, ``api.py``, ``voice/router.py``
   * - Worker & crawler
     - Maintain embeddings, fetch documents, enrich metadata
     - ``worker.py``, ``crawler/run_crawl.py``, ``knowledge_service/``
   * - Storage & LLM runtimes
     - Persist state (Mongo, Redis, GridFS) and generate answers (Ollama,
       YaLLM, Azure OpenAI)
     - ``models.py``, ``backend/settings.py``, ``backend/llm_client.py``

1. Knowledge ingestion lifecycle
--------------------------------

**Objective:** transform raw content (uploads or crawls) into searchable
chunks with metadata and embeddings stored in MongoDB, Redis and optional
Qdrant.

1. Operator initiates an upload or crawl via the admin UI.  Calls land in
   ``/api/v1/admin/knowledge`` handlers inside ``api.py``; payloads are
   validated with Pydantic models from ``models.py``.
2. Uploads stream through ``_read_qa_upload`` (enforcing MIME/size checks)
   and are persisted to Mongo/GridFS.  Crawl requests enqueue jobs handled by
   ``crawler/run_crawl.py`` which deduplicates targets, optionally renders
   SPA content with Playwright, and emits progress to Redis so the UI can
   display status bars.
3. Completion events schedule Celery tasks (``worker.py``) that read the new
   documents, compute embeddings via ``vectors.py`` (YaLLM/Ollama) and update
   Redis or Qdrant.  The worker keeps per-project watermarks to avoid
   reprocessing unchanged documents.
4. Optional summarisation and teaser enrichment happen inside
   ``knowledge_service/`` where tasks batch LLM calls, cache summaries in
   Redis and expose metrics for admin visibility.
5. Analytics entries (e.g., ``knowledge_ingest_completed``) are logged to
   Mongo collections with TTL indexes so dashboards surface the latest events
   without manual pruning.

.. graphviz::
   :name: knowledge-flow
   :align: center

   digraph knowledge_flow {
       rankdir=LR;
       node [shape=box, style="rounded", fontname="Helvetica"];

       Operator [label="Operator\n(Admin UI)"];
       API [label="FastAPI admin routers\n(api.py)"];
       Storage [label="MongoDB + GridFS"];
       Crawler [label="Crawler\n(run_crawl.py)"];
       Worker [label="Celery worker\n(worker.py)"];
       Redis [label="Redis / Qdrant\n(vectors)"];
       Enrichment [label="knowledge_service\n(summaries)"];

       Operator -> API [label="upload/crawl request"];
       API -> Storage [label="documents, blobs"];
       API -> Crawler [label="crawl jobs"];
       Crawler -> Storage [label="clean text"];
       Storage -> Worker [label="change stream / task"];
       Worker -> Redis [label="embeddings"];
       Worker -> Storage [label="metadata updates"];
       Worker -> Enrichment [label="summary tasks"];
       Enrichment -> Storage [label="teasers, captions"];
   }

2. Conversational answering workflow
------------------------------------

**Objective:** serve grounded answers for chat/REST clients with full audit
logging and analytics stored per project.

1. Widget/bot sends ``POST /api/v1/llm/ask`` with a project slug, session ID,
   current turn text and optional attachment references.
2. ``api.py`` normalises the project, loads tenant config (prompt, model,
   connectors) from Mongo and retrieves prior dialog turns; sessions are
   capped by configurable history depth (see ``settings.SessionSettings``).
3. ``retrieval/search.py`` aggregates candidates from Redis vectors,
   fallback keyword search, and optional Qdrant collections.  Results are
   scored, deduplicated and trimmed to ``settings.RetrievalSettings`` limits.
4. ``backend.llm_client`` assembles the final prompt (system instructions,
   conversational context, citations) and streams the call to the configured
   LLM backend.  SSE/WebSocket handlers relay partial tokens immediately to
   the client.
5. Completed answers, citations, tool invocations and telemetry are persisted
   in Mongo (`dialog_messages`, `analytics_events`).  Redis caches store the
   final response for a short TTL to unblock retries or bot replays.
6. Optional post-processing triggers (mail connector, voice TTS, bot
   dispatchers) react to structured tool outputs returned by the LLM.

.. graphviz::
   :name: conversation-flow
   :align: center

   digraph conversation_flow {
       rankdir=LR;
       node [shape=box, style="rounded", fontname="Helvetica"];

       Client [label="Client\n(widget/bot)"];
       API [label="FastAPI\n(api.py)"];
       Sessions [label="Sessions\n(Mongo)"];
       Retrieval [label="retrieval/search.py"];
       Redis [label="Redis cache/\nvector store"];
       Qdrant [label="Qdrant\n(optional)"];
       LLM [label="backend.llm_client\n(Ollama/YaLLM)"];
       Analytics [label="Mongo analytics\n+ logs"];

       Client -> API [label="POST /llm/ask"];
       API -> Sessions [label="load history"];
       Sessions -> API [label="context"];
       API -> Retrieval [label="query"];
       Retrieval -> Redis;
       Retrieval -> Qdrant;
       Redis -> Retrieval;
       Qdrant -> Retrieval;
       Retrieval -> API [label="ranked snippets"];
       API -> LLM [label="prompt stream"];
       LLM -> API [label="tokens"];
       API -> Client [label="SSE/WebSocket"];
       API -> Analytics [label="dialog, metrics"];
   }

Verification notes
~~~~~~~~~~~~~~~~~~

* ``api.py`` enforces project scoping before any retrieval/LLM call; improper
  slugs return 404 and never reach vector queries.
* Sessions throttle concurrent requests via Redis semaphores (``session_lock``)
  to prevent inconsistent histories when browsers double-submit.
* Attachments referenced in chat requests are resolved through GridFS IDs in
  ``models.AttachmentReference`` and validated per project ownership.
* Response caches include the hash of the compiled prompt.  If project prompts
  change, cached responses automatically miss and new answers are generated.

3. Voice assistant streaming pipeline
-------------------------------------

**Objective:** manage bi-directional audio conversations with low latency by
stitching recognition, dialog management and TTS.

Flow summary:

1. The voice widget establishes a WebSocket connection to
   ``/api/v1/voice/ws``.  ``voice/router.py`` authenticates the project key,
   initialises a session (``voice/sessions.py``) and hands control to the
   dialog manager.
2. Audio chunks stream from the browser.  Depending on configured provider,
   ``voice/recognizer.py`` routes them to SimpleRecognizer (demo) or future
   Whisper/Vosk integrations.  Partial hypotheses are pushed back to the
   widget for live captions.
3. Recognized text feeds ``voice/dialogue.py`` which applies intent rules,
   interacts with the same retrieval/LLM pipeline (via ``api.ask`` helpers)
   and tracks multi-turn state (listening, processing, speaking, error).
4. The response is synthesized through ``voice/synthesizer.py``.  Today this
   uses ``SimpleTTSProvider`` but the abstraction is ready for ElevenLabs or
   Azure Neural TTS.
5. Audio buffers stream to the browser, while transcripts, timing metrics and
   any command invocations are stored in Mongo (``voice_sessions`` collection)
   for audit.

.. graphviz::
   :name: voice-flow
   :align: center

   digraph voice_flow {
       rankdir=LR;
       node [shape=box, style="rounded", fontname="Helvetica"];

       Widget [label="Voice widget\n(TypeScript)"];
       Router [label="voice/router.py\n(WebSocket)"];
       Recognizer [label="voice/recognizer.py\n(Simple/Whisper/Vosk)"];
       Dialogue [label="voice/dialogue.py\n(intent manager)"];
       AskAPI [label="api.ask helpers\n(retrieval + LLM)"];
       Synth [label="voice/synthesizer.py\n(TTS providers)"];

       Widget -> Router [label="WS connect"];
       Router -> Recognizer [label="audio chunks"];
       Recognizer -> Router [label="partial text"];
       Router -> Dialogue [label="final text"];
       Dialogue -> AskAPI [label="LLM query"];
       AskAPI -> Dialogue [label="answer"];
       Dialogue -> Synth [label="text to voice"];
       Synth -> Router [label="audio buffer"];
       Router -> Widget [label="streamed PCM"];
   }

Voice session state machine
~~~~~~~~~~~~~~~~~~~~~~~~~~~

State transitions are enforced inside ``voice/state.py`` with guards around
timeout/errors:

``idle -> listening -> processing -> speaking -> idle``

* ``idle`` – awaiting push-to-talk; timers ensure the session expires after
  inactivity (default 2 minutes).
* ``listening`` – microphone streaming; VAD (future) or manual actions end the
  capture.
* ``processing`` – recognition finished, dialog/LLM call running.  Backpressure
  prevents new audio until completion.
* ``speaking`` – TTS streaming; the widget may interrupt and force a return to
  ``listening`` for barge-in scenarios.

4. Business events and side-effects
-----------------------------------

.. list-table::
   :header-rows: 1

   * - Event
     - Trigger
     - Handler & storage
     - Side effects
   * - ``knowledge_ingest_completed``
     - Upload/crawl success
     - ``worker.py`` → Mongo ``knowledge_events``
     - Recalculate embeddings, schedule summaries
   * - ``dialog_message_created``
     - Chat answer streamed
     - ``api.py`` → Mongo ``dialog_messages``
     - Updates analytics counters, surfaces in admin logs
   * - ``voice_session_closed``
     - WebSocket disconnect/timeout
     - ``voice/router.py`` → Mongo ``voice_sessions``
     - Releases Redis locks, finalises metrics
   * - ``mail_command_planned`` / ``mail_command_confirmed``
     - Tool output from LLM planner
     - ``api.py`` mail helpers → Redis ``mail:plan:*`` + Mongo audit
     - Allows operator approval, ensures idempotency

5. Validation & observability checklist
---------------------------------------

* **Authentication & scoping** – admin APIs require Basic auth and
  ``_require_super_admin`` guards; public APIs enforce project tokens or
  widget secrets.  Voice/WebSocket connections validate project & session IDs.
* **Input sanitisation** – uploads and crawler endpoints validate MIME/size,
  enforce URL allowlists and run HTML stripping in ``crawler/utils.py``.
* **Rate limiting** – current implementation throttles Telegram bots and
  session creation; ``TODO.md`` tracks broader rate-limit roll-out (Phase 0/1).
* **Caching & retries** – Celery tasks use exponential backoff for embedding
  updates; voice recognizers retry chunk submission when GPU backpressure is
  detected.
* **Observability** – ``core/metrics.py`` exposes request/error counters,
  voice modules log latency histograms, and admin dashboards leverage Mongo
  aggregations for per-project analytics.
* **Disaster recovery** – backup endpoints (``/api/v1/backup/*``) follow the
  checklist in ``SECURITY_BACKUP_CHECKLIST.md``; remediation tasks are
  prioritised under Phase 0 of ``TODO.md``.

Use this document alongside ``components.rst`` to onboard engineers: it
captures how data travels between modules, what to monitor, and which
controls must remain intact whenever the workflow is modified.
