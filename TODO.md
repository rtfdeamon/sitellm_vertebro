# SiteLLM Vertebro – Work Backlog

> Source of truth for outstanding work pulled from the “Полный анализ проекта SiteLLM Vertebro” PDF, the QA import audit packs, and local repo review. Trackable items are grouped by the five-phase roadmap (security ➜ refactors ➜ testing ➜ infrastructure ➜ documentation). Every task lists the concrete files to touch, expected behaviour, and validation strategy so it can be delegated directly to Cursor Agents or engineers.

---

## Phase 0 – Backup Security Remediation (ASAP, 6–10 ч)

- [ ] **0.1 CSRF protection for backup endpoints (`app.py`, `admin/js/backup.js`, `.env`)**  
  - Вставить `CSRFProtectionMiddleware`, настроить `ALLOWED_ORIGINS`, гарантировать что backup UI отправляет `X-Requested-With`.  
  - **Tests:** запрос без Origin → 403, допустимый Origin → 200, UI флоу не ломается.

- [ ] **0.2 Audit logging & monitoring для `_require_super_admin` (`app.py`, observability)**  
  - Заменить функцию на версию из `SECURITY_BACKUP_FIXES.py`, логировать `unauthorized_super_admin_access_attempt` и `super_admin_access_granted`, добавить alert/cron проверки логов.  
  - **Tests:** обычный админ получает 403 и лог, супер-админ проходит + событие.

- [ ] **0.3 Валидатор путей backup restore (`backup/validators.py`, `app.py:backup_restore`)**  
  - Создать модуль с проверками traversal/null-byte/allowed-folder и подключить в endpoint.  
  - **Tests:** traversal/чужая папка/null-byte → 400, валидный путь → проходит.

- [ ] **0.4 Restore confirmation handshake (`admin/js/backup.js`, `app.py`)**  
  - Двойное подтверждение в UI + обязательный заголовок `X-Confirmation: restore-confirmed` с логированием отказов.  
  - **Tests:** отсутствие заголовка → 400, UI не шлёт запрос без двух подтверждений.

- [ ] **0.5 Rate limiting backup API (`requirements.txt`, `app.py`)**  
  - Подключить SlowAPI limiter (Redis/memory), ограничить `/status` 30/min, `/run` 5/hour, `/restore` 2/hour, вернуть 429 при превышении.  
  - **Tests:** 6-й запрос на `/run` за минуту получает 429, метрики/логи фиксируют событие.

- [ ] **0.6 Security headers middleware (`app.py`)**  
  - Добавить `SecurityHeadersMiddleware` из чеклиста, конфигурировать через `DEBUG` флаг.  
  - **Tests:** `/admin` возвращает CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy.

- [ ] **0.7 Sanitized backup errors (`backup/service.py`)**  
  - Реализовать `sanitize_error_message`, оборачивать ошибки `perform_backup/perform_restore/_download_archive`.  
  - **Tests:** при `DEBUG=false` ответы содержат только тип ошибки, при `DEBUG=true` — подробности.

- [ ] **0.8 Deployment runbook**  
  - Следовать pre-flight/back-up шагам, рестартовать приложение после патчей, выполнить post-deploy проверки/rollback план из `SECURITY_BACKUP_CHECKLIST.md`.

---

## Phase 1 – Critical Security Fixes (Week 1–2)

- [ ] **1.1 Comprehensive input validation (`app.py`, `api.py`, `crawler/run_crawl.py`, `models.py`)**  
  - Add Pydantic validators for upload size (100 MB), MIME whitelist, magic-number check, Unicode normalization, HTML escaping, and length caps (Q≤1000, A≤10000).  
  - Apply validators across admin/public endpoints, including crawler URL whitelists/blacklists, protocol enforcement, redirect caps, and 30 s timeouts.  
  - Implement file read timeout via `asyncio.wait_for`, integrate CSV delimiter detection, per-IP upload throttling (10/hour) in Redis, and ClamAV hook for binaries.  
  - **Tests:** unit tests for validator edge-cases + integration test for QA upload failure modes; crawler SSRF regression test.

- [ ] **1.2 Rate limiting & attack surface hardening (`backend/security.py` new, `app.py`, `api.py`, `mongo.py`, `admin/js/*`)**  
  - Introduce Redis-backed limiters (100 read/min/IP, 10 write/min/IP, 1000 req/hour/user) with `Retry-After`.  
  - Sanitize Mongo queries (operator whitelist, escaping), audit crawler inputs for SSRF, add CSP headers + DOMPurify + CSRF tokens in admin/widget forms.  
  - Add `_require_super_admin` logging (unauthorized attempts) and security middleware for private-IP blocking.  
  - **Tests:** security suite covering rate-limit, CSRF, SSRF, and NoSQL injection cases.

- [ ] **1.3 QA import backend/frontend parity (`app.py: _read_qa_upload`, `admin/js/index.js`, `QA_IMPORT_*`)**  
  - Enforce file-size/empty checks, better CSV decoding (Sniffer, multi-encoding), Excel error reporting, text-length truncation, duplicate detection, and progress statuses.  
  - Frontend must disable submit button, show file-size precheck, progress indicator, and success/failure toasts.  
  - Update docs/manuals with new limits and troubleshooting table.  
  - **Tests:** integration tests for CSV with `;` and `\t`, corrupt Excel, zero-byte file, over-long entries; Cypress/UI test for disabled button behaviour.

- [ ] **1.4 Security automation (`bandit.yaml`, `.pre-commit-config.yaml`, CI)**  
  - Add Bandit config (rules B201–B609), wire into `pre-commit` and CI with JSON reports; ensure fixes (pickles → json, secure HTTP, secrets for tokens).  
  - Generate markdown security report and store under `security/REPORT.md`.  
  - **Tests:** CI must fail on HIGH/MEDIUM issues; include sample insecure snippet test to verify Bandit catches regressions.

---

## Phase 2 – Refactor & Performance (Week 3–4)

- [x] **2.1 Break down `app.py` monolith (new `app/` package)** ✅ COMPLETED  
  - ✅ Created `app/main.py` (~106 LOC) for factory + middleware.  
  - ✅ Moved routers into `app/routers/{admin,backup,stats,projects,knowledge,llm}.py`, services into `app/services/auth.py`.  
  - ✅ Updated imports, dependency injection, and maintained backwards-compatible ASGI entrypoint (`app:app`).  
  - ✅ Reduced `app.py` from ~6000 to ~5000 lines, removed ~1000 lines of duplicate code
  - ✅ Moved 73+ endpoints to routers
  - ✅ All routers compile without errors
  - **Tests:** smoke tests for every router, regression run of entire pytest suite.

- [ ] **2.2 Performance optimization**  
  - Mongo: enable connection pooling (min 10 / max 100), ensure indexes for frequent queries, add projections and bulk ops.  
  - Redis caching layer (`backend/cache_manager.py`) with decorators for LLM results (1 h), embeddings (24 h), search (15 min); invalidation hooks on document updates.  
  - Retrieval: implement RRF fusion, optional reranker batching, dedup by hashed content, vector search caching, HNSW parameter tuning.  
  - API: enable gzip, SSE chunk tuning, ETag support; convert blocking HTTP to async with pooled clients.  
  - **Tests:** benchmark script updates verifying p95 <500 ms; unit tests for cache manager, dedup logic; load tests via `scripts/benchmark.py`.

- [ ] **2.3 Async crawler robustness (`crawler/run_crawl.py`)**  
  - Add retry logic with classified errors, domain blacklist, 30 s timeout, max 5 redirects, and connection pooling for aiohttp.  
  - Emit structured errors for observability; ensure queue dedupe persists.  
  - **Tests:** simulated failure scenarios + queue dedup tests.

- [ ] **2.4 Knowledge summarisation service upgrade (`knowledge/summary.py`, `knowledge_service/`, `backend/llm_client.py`)**  
  - Batch calls to the LLM when summarising multiple documents, reuse streaming chunks, and enforce consistent truncation with Unicode-safe ellipsis.  
  - Cache summary/teaser/image caption outputs in Redis with invalidation on document updates; optional offline summarisation via Celery tasks.  
  - Surface metrics (success/failure counts, latency, token usage) and structured logs for summary failures; expose configuration in admin UI.  
  - Harden prompt templates (locale fallback, safe HTML stripping) and support per-project model overrides with graceful fallback if the requested model is missing.  
  - **Tests:** unit tests for prompt building/truncation, async mocking of `llm_client.generate`, caching behaviour, and project override paths.

---

## Phase 3 – Testing & Quality (Week 5–6)

- [ ] **3.1 Testing framework uplift**  
  - Expand dev deps: `pytest-cov`, `pytest-asyncio`, `pytest-xdist`, `pytest-mock`, `coverage[toml]`.  
  - Add `pytest.ini` (strict markers, coverage config, min 80%) and `conftest` fixtures for Mongo/Redis testcontainers.  
  - Organize tests into `tests/unit`, `tests/integration`, `tests/performance`, `tests/security`, `tests/e2e`; seed representative examples from PDF.  
  - **Goal:** 90 %+ total coverage; unit ≥95 % for business logic, integration ≥85 %, perf tests enforce p95 <500 ms, zero critical security findings.

- [ ] **3.2 CI/CD quality gates (`.github/workflows/ci.yml`)**  
  - Steps: `ruff format --check`, `ruff check`, `black --check`, `mypy`, `bandit`, `pytest --cov --cov-report=xml --cov-fail-under=90`, performance smoke (p95 <=4 s).  
  - Upload coverage + benchmark artifacts; fail build if metrics regress vs previous baseline.  
  - **Tests:** dry-run workflow locally via `act` or equivalent.

- [ ] **3.3 QA import regression suite**  
  - Dedicated integration test verifying CSV/XLSX import, front-end file guard, and admin API responses; add fixtures in `tests/integration/test_qa_import.py`.  
  - Maintain sample fixtures under `tests/fixtures/qa_import/`.

- [ ] **3.4 Summary/reading teaser coverage (`knowledge/summary.py`, `tests/unit/test_summary.py`)**  
  - Add unit tests covering model selection, truncation, empty-content fallbacks, and exception paths for document summaries, reading segments, and image captions.  
  - Create async fixtures for fake `llm_client.generate` streams, validate Unicode handling, and measure coverage of error logging branches.  
  - **Goal:** 95 %+ coverage of summary helpers to catch regressions when changing LLM prompts or models.

---

## Phase 4 – Production Infrastructure (Week 7–8)

- [ ] **4.1 Observability stack (`observability/`, `docker/`, `docs/`)**  
  - Instrument FastAPI, Mongo, Redis with OpenTelemetry; add Grafana dashboard JSON matching PDF (request rate, latency, error rate, cache hit, DB pool, LLM tokens).  
  - Extend Prometheus metrics (request_count, latency, cache hits) and expose /metrics in production configs.  
  - Document tracing setup and include Grafana provisioning file.

- [ ] **4.2 Disaster recovery & backups (`backup/advanced_backup.py`, `deploy/`, runbooks)**  
  - Build AdvancedBackupManager with S3/Yandex storage, AES-256 encryption, retention policy (7 daily/4 weekly/12 monthly), checksum verification, automated restore tests, alerts.  
  - Automate backup scheduling (systemd timers or k8s CronJob).  
  - Draft runbooks for backup creation/restoration, disaster scenarios, and chaos testing plan (network partitions, node failure, load spikes).  
  - **Tests:** simulated restore in CI/staging weekly; automated checksum verification.

- [ ] **4.3 High availability deployment**  
  - Compose/Kubernetes manifests for Mongo replica set, Redis Sentinel, Qdrant clustering, API HPA (min 3 replicas, CPU 70%), readiness/liveness probes, autoscaling behaviour from PDF snippet.  
  - Add infra docs plus instructions for load balancer (nginx/traefik) with health checks.  
  - **Tests:** staging deployment verifying failover + load tests under failover.

---

## Phase 5 – Documentation & Developer Experience (Week 9–10)

- [ ] **5.1 Full documentation system (MkDocs Material)**  
  - Create docs tree per PDF (`index.md`, `getting-started/`, `api/`, `architecture/`, `guides/`, `tutorials/`, `reference/`).  
  - Add PlantUML/Mermaid diagrams (C4, sequence, data flow), OpenAPI 3.1 spec with Swagger/ReDoc integration, API auth examples, rate-limit info, and error codes.  
  - Migrate existing Sphinx content (architecture/components/workflows) into new sections; link Russian manuals as localized guides.  
  - **Tests:** `mkdocs build` in CI, link checker, doc coverage via `pydocstyle`.

- [ ] **5.2 Developer tooling & automation**  
  - `Makefile` targets (install/test/lint/format/check/docs/serve/clean/dev-run/dev-worker/dev-test/prod-*).  
  - VS Code `tasks.json` for running the Make targets, `.vscode/settings.json` for formatter/linting defaults.  
  - `.pre-commit-config.yaml` with Ruff (lint+format), Black, isort (if needed), mypy, bandit, commitlint; ensure `pre-commit install` baked into dev-setup instructions.  
  - `.cursorrules` capturing standards, `.cursor/commands/` and background agents JSON as in PDF.  
  - **Tests:** run `make check`, ensure pre-commit hook executes on sample commit.

- [ ] **5.3 Knowledge sharing**  
  - Document quick-start (15 min), contributing guide, testing guide, debugging cheatsheet, performance optimization manual, and user runbooks (admin panel, widget embed, bot setup, Q&A import).  
  - Update README with roadmap linkage, configuration tables (.env), CI badge, docs link, support contact.

---

## Voice Assistant Production Enhancements (Post-MVP)

### Production Speech Providers

- [ ] **VA.1 Whisper integration (`voice/recognizer.py`, GPU infra)**  
  - Реализовать streaming Whisper inference с auto language detection, управлением сессиями и fallback на CPU.  
  - **Tests:** latency/streaming benchmarks, интеграция с WebSocket router.

- [ ] **VA.2 Vosk offline recognizer (`voice/recognizer.py`)**  
  - Добавить офлайн ASR с модельным менеджером и настройками ресурсов для edge/air-gapped инсталляций.  
  - **Tests:** офлайн юнит-тесты + smoke в CI.

- [ ] **VA.3 ElevenLabs TTS provider (`voice/synthesizer.py`)**  
  - Интегрировать API-ключ, emotion params, voice caching + error handling; переключение через конфиг.  
  - **Tests:** mock ElevenLabs API, проверить кэш и таймауты.

- [ ] **VA.4 Azure Neural TTS provider (`voice/synthesizer.py`)**  
  - Поддержать регион/voice selection, streaming chunks, retries.  
  - **Tests:** контрактные тесты с заглушкой SDK.

### Streaming Capabilities

- [ ] **VA.5 Audio chunk streaming (`voice/router.py`, WebSocket infra)**  
  - Передача PCM чанков от клиента к Whisper/Vosk, контроль backpressure, адаптация ping/pong.  
  - **Tests:** WebSocket integration, нагрузочные тесты.

- [ ] **VA.6 Real-time transcription**  
  - Публикация промежуточных транскриптов в канал клиента, устойчивость к reconnect.  
  - **Tests:** браузерные диалоги + e2e сценарии.

- [ ] **VA.7 Streaming synthesis**  
  - Возврат TTS чанков по мере готовности, совместимость с ElevenLabs/Azure streaming API.  
  - **Tests:** smokes с фальшивым провайдером, регресс VAD/плеера.

### Dialog Engine & UX

- [ ] **VA.8 Advanced context management**  
  - Расширить контекст на длинные разговоры (rollback windows, summary slots, persona injection).  
  - **Tests:** многошаговые диалоговые сценарии.

- [ ] **VA.9 Multi-turn conversation tracking**  
  - Улучшить журнал событий, восстановление состояния после reconnect, аналитика переходов.  
  - **Tests:** browser dialog suite с продолжительными сценариями.

- [ ] **VA.10 Advanced feature backlog**  
  - Audio visualizations, веб-навигация, voice cloning/training UI, расширенное многоязычие, эмоции, VAD (см. `REMAINING_TASKS.md`).  
  - **Tests:** определить по мере реализации.

### Testing Debt

- [ ] **VA.11 Починить `test_voice_training_api.py`**  
  - Обновить pytest-asyncio fixtures/markers, убрать legacy зависимость, гарантировать прохождение 3 падающих тестов.  
  - **Tests:** `pytest tests/voice/test_voice_training_api.py`.

---

## Quality Targets & Metrics

- Test coverage 95 % unit / 85 % integration / 100 % critical flows; enforce via `pytest --cov` + coverage badge.  
- Type coverage 100 % (mypy strict), cyclomatic complexity ≤10, code duplication ≤3 %.  
- Security: zero outstanding HIGH/MEDIUM Bandit findings, CSRF/SSRF mitigations documented, rate limiting verified.  
- Performance: API p95 <500 ms, crawler throughput thresholds defined, automatic alerts for >10 % degradation; benchmark deltas stored under `benchmarks/`.  
- Documentation coverage: MkDocs site with API + architecture diagrams, runbooks, and localized manuals referenced from README.

---

## Tracking & Ownership

- Convert each checkbox into a GitHub issue tagged with the phase/priority; link back here for status.  
- Keep this file updated after each sprint (include ✅ when merged, add owner initials/dates if helpful).  
- Cursor Agent prompts from the PDF are suitable as issue descriptions—paste them directly into the issue body for precise automation instructions.
