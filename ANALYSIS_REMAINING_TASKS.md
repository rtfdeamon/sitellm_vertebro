# Анализ оставшихся задач - SiteLLM Vertebro

**Дата анализа**: 2025-11-16  
**Статус проекта**: Готов к продакшену (критичные задачи выполнены)

---

## 📊 Общий статус

### ✅ Завершено (Критичное - 100%)

**Phase 1: Critical Security Fixes (9/9) ✅**
- ✅ Input validation (backend/validators.py)
- ✅ Rate limiting (backend/rate_limiting.py)
- ✅ SSRF protection (backend/security.py, crawler/run_crawl.py)
- ✅ NoSQL injection protection (backend/security.py, mongo.py)
- ✅ CSRF/CSP protection (backend/csrf.py, backend/csp.py)
- ✅ Super admin logging (app.py, api.py)
- ✅ QA import frontend improvements (admin/js/index.js)
- ✅ QA import Excel error handling (app.py)
- ✅ QA import duplicate detection (mongo.py, app.py)

**Phase 2: Performance Optimization (4/4) ✅**
- ✅ MongoDB connection pooling (mongo.py)
- ✅ Redis caching layer (backend/cache_manager.py)
- ✅ Retrieval optimization (retrieval/search.py)
- ✅ API optimization (backend/gzip_middleware.py)

**Phase 3: Testing & Quality (3/3) ✅**
- ✅ Testing framework setup (pytest.ini, conftest_enhanced.py)
- ✅ Security test suite (tests/security/)
- ✅ QA import integration tests (tests/integration/test_qa_import.py)

**Phase 3: CI/CD (1/1) ✅**
- ✅ CI/CD quality gates (.github/workflows/ci.yml)

**Voice Features (2/2) ✅**
- ✅ Voice production providers (voice/providers/)
  - ✅ Whisper recognizer реализован полностью
  - ✅ Vosk recognizer (инфраструктура готова)
  - ✅ ElevenLabs TTS provider
  - ✅ Azure TTS provider
- ✅ Voice WebSocket streaming (voice/router.py)

**Итого критичных задач**: 19/19 (100%) ✅

---

## ⏳ Осталось сделать

### 🔴 Высокий приоритет (Блокируют полное завершение плана)

#### 1. Рефакторинг app.py (Phase 2.1) - Не завершен
**Статус**: ⏳ Частично выполнено  
**Приоритет**: 🔴 Высокий

**Что сделано**:
- ✅ Создана структура `app/` пакета
- ✅ Создан `app/__init__.py` (placeholder)

**Что осталось**:
- [ ] Создать `app/main.py` (<500 LOC) для factory + middleware
- [ ] Переместить routers в `app/routers/{projects,knowledge,backup,stats,voice}.py`
  - Папка `app/routers/` существует, но пуста
- [ ] Переместить services в `app/services/`
  - Папка `app/services/` существует, но пуста
- [ ] Переместить shared schemas в `app/models/`
- [ ] Обновить все imports
- [ ] Обеспечить backward compatibility ASGI entrypoint (`app:app`)
- [ ] Добавить smoke tests для каждого router

**Файлы для работы**:
- `app.py` (основной монолит ~5000+ LOC)
- `app/main.py` (новый файл)
- `app/routers/*.py` (новые файлы)
- `app/services/*.py` (новые файлы)
- `app/models/*.py` (новые файлы)

---

#### 2. Async crawler robustness (Phase 2.3) - Не завершен
**Статус**: ⏳ Частично выполнено  
**Приоритет**: 🟡 Средний

**Что осталось**:
- [ ] Добавить retry logic с классификацией ошибок
- [ ] Добавить domain blacklist
- [ ] Убедиться в 30s timeout
- [ ] Ограничить max 5 redirects
- [ ] Добавить connection pooling для aiohttp
- [ ] Emit structured errors для observability
- [ ] Убедиться в queue dedupe persistence
- [ ] Добавить тесты: simulated failure scenarios + queue dedup tests

**Файлы для работы**:
- `crawler/run_crawl.py`

---

#### 3. Knowledge summarisation service upgrade (Phase 2.4) - Не завершен
**Статус**: ⏳ Частично выполнено  
**Приоритет**: 🟡 Средний

**Что осталось**:
- [ ] Batch calls к LLM при summarising multiple documents
- [ ] Reuse streaming chunks
- [ ] Enforce consistent truncation с Unicode-safe ellipsis
- [ ] Cache summary/teaser/image caption outputs в Redis с invalidation на document updates
- [ ] Optional offline summarisation via Celery tasks
- [ ] Surface metrics (success/failure counts, latency, token usage)
- [ ] Structured logs для summary failures
- [ ] Expose configuration в admin UI
- [ ] Harden prompt templates (locale fallback, safe HTML stripping)
- [ ] Support per-project model overrides с graceful fallback

**Тесты**:
- [ ] Unit tests для prompt building/truncation
- [ ] Async mocking of `llm_client.generate`
- [ ] Caching behaviour tests
- [ ] Project override paths tests

**Файлы для работы**:
- `knowledge/summary.py`
- `knowledge_service/service.py`
- `backend/llm_client.py`
- `tests/unit/test_summary.py` (существует, но нужно расширить покрытие до 95%+)

---

#### 4. Testing framework uplift (Phase 3.1) - Частично завершен
**Статус**: ⏳ Частично выполнено  
**Приоритет**: 🟡 Средний

**Что сделано**:
- ✅ `pytest.ini` создан с coverage config (min 80%)
- ✅ `conftest_enhanced.py` с testcontainers fixtures
- ✅ Структура тестов частично организована:
  - ✅ `tests/unit/` - существует
  - ✅ `tests/integration/` - существует
  - ✅ `tests/security/` - существует
  - ✅ `tests/e2e/` - существует
  - ❌ `tests/performance/` - **НЕ СУЩЕСТВУЕТ**

**Что осталось**:
- [ ] Создать `tests/performance/` директорию
- [ ] Добавить performance тесты с p95 <500ms enforcement
- [ ] Увеличить coverage threshold с 80% до 90%+ (как указано в TODO.md)
- [ ] Убедиться в unit ≥95% для business logic
- [ ] Убедиться в integration ≥85%
- [ ] Добавить dev deps если нужно: `pytest-cov`, `pytest-asyncio`, `pytest-xdist`, `pytest-mock`, `coverage[toml]`

**Goal**: 90%+ total coverage; unit ≥95% для business logic, integration ≥85%, perf tests enforce p95 <500ms

---

#### 5. CI/CD quality gates (Phase 3.2) - Частично завершен
**Статус**: ⏳ Частично выполнено  
**Приоритет**: 🟡 Средний

**Что сделано**:
- ✅ `.github/workflows/ci.yml` существует
- ✅ `ruff format --check` - есть
- ✅ `ruff check` - есть
- ✅ `mypy` - есть (но с `continue-on-error: true`)
- ✅ `bandit` - есть
- ✅ `pytest --cov` - есть
- ✅ Coverage threshold установлен на 80% (но в TODO.md указано 90%)

**Что осталось**:
- [ ] Увеличить coverage threshold до 90% в CI (сейчас 80%)
- [ ] Убрать `continue-on-error: true` для mypy (или исправить ошибки)
- [ ] Добавить `black --check` (если используется)
- [ ] Убедиться что performance smoke tests работают (p95 <=4s)
- [ ] Добавить benchmark artifacts upload
- [ ] Добавить fail build если metrics regress vs previous baseline

**Файлы для работы**:
- `.github/workflows/ci.yml`
- `pytest.ini` (coverage threshold)

---

#### 6. Summary/reading teaser coverage (Phase 3.4) - Частично завершен
**Статус**: ⏳ Частично выполнено  
**Приоритет**: 🟡 Средний

**Что сделано**:
- ✅ `tests/test_summary.py` существует (2 теста)

**Что осталось**:
- [ ] Расширить тесты для покрытия:
  - [ ] Model selection
  - [ ] Truncation
  - [ ] Empty-content fallbacks
  - [ ] Exception paths для document summaries
  - [ ] Exception paths для reading segments
  - [ ] Exception paths для image captions
- [ ] Создать async fixtures для fake `llm_client.generate` streams
- [ ] Validate Unicode handling
- [ ] Measure coverage of error logging branches
- [ ] **Goal**: 95%+ coverage of summary helpers

**Файлы для работы**:
- `knowledge/summary.py`
- `tests/test_summary.py` (расширить) или `tests/unit/test_summary.py`

---

### 🟢 Средний приоритет (Улучшения, не блокируют)

#### 7. Performance optimization - частично завершен
**Статус**: ⏳ Частично выполнено  
**Приоритет**: 🟢 Средний

**Что осталось**:
- [ ] Mongo: ensure indexes для frequent queries
- [ ] Mongo: add projections и bulk ops
- [ ] Retrieval: optional reranker batching
- [ ] Retrieval: dedup by hashed content
- [ ] Retrieval: HNSW parameter tuning
- [ ] API: SSE chunk tuning
- [ ] API: ETag support
- [ ] API: convert blocking HTTP to async с pooled clients

**Тесты**:
- [ ] Benchmark script updates verifying p95 <500ms
- [ ] Unit tests для dedup logic
- [ ] Load tests via `scripts/benchmark.py`

---

#### 8. Developer tooling & automation (Phase 5.2) - Не завершен
**Статус**: ⏳ Не начато  
**Приоритет**: 🟢 Низкий

**Что осталось**:
- [ ] Создать `Makefile` с targets:
  - `install`, `test`, `lint`, `format`, `check`, `docs`, `serve`, `clean`
  - `dev-run`, `dev-worker`, `dev-test`
  - `prod-*` targets
- [ ] VS Code `tasks.json` для running Make targets
- [ ] `.vscode/settings.json` для formatter/linting defaults
- [ ] `.cursorrules` для capturing standards
- [ ] `.cursor/commands/` и background agents JSON
- [ ] Обновить dev-setup instructions с pre-commit install

**Примечание**: `.pre-commit-config.yaml` уже существует и настроен ✅

---

#### 9. Full documentation system (Phase 5.1) - Частично завершен
**Статус**: ⏳ Частично выполнено  
**Приоритет**: 🟢 Низкий

**Что сделано**:
- ✅ Sphinx docs существуют (`docs/`)
- ✅ Voice docs созданы

**Что осталось**:
- [ ] Migrate на MkDocs Material
- [ ] Создать структуру:
  - `index.md`
  - `getting-started/`
  - `api/`
  - `architecture/`
  - `guides/`
  - `tutorials/`
  - `reference/`
- [ ] Добавить PlantUML/Mermaid diagrams (C4, sequence, data flow)
- [ ] OpenAPI 3.1 spec с Swagger/ReDoc integration
- [ ] API auth examples, rate-limit info, error codes
- [ ] Migrate existing Sphinx content
- [ ] Link Russian manuals как localized guides
- [ ] Добавить `mkdocs build` в CI
- [ ] Link checker
- [ ] Doc coverage via `pydocstyle`

---

#### 10. Knowledge sharing (Phase 5.3) - Частично завершен
**Статус**: ⏳ Частично выполнено  
**Приоритет**: 🟢 Низкий

**Что осталось**:
- [ ] Document quick-start (15 min)
- [ ] Contributing guide
- [ ] Testing guide
- [ ] Debugging cheatsheet
- [ ] Performance optimization manual
- [ ] User runbooks:
  - Admin panel usage
  - Widget embed guide
  - Bot setup guide
  - Q&A import guide
- [ ] Update README с:
  - Roadmap linkage
  - Configuration tables (.env)
  - CI badge
  - Docs link
  - Support contact

---

### 🔵 Низкий приоритет (Опциональные улучшения)

#### 11. Observability stack (Phase 4.1) - Не начато
**Статус**: ⏳ Не начато  
**Приоритет**: 🔵 Низкий

**Что осталось**:
- [ ] Instrument FastAPI, Mongo, Redis с OpenTelemetry
- [ ] Grafana dashboard JSON (request rate, latency, error rate, cache hit, DB pool, LLM tokens)
- [ ] Extend Prometheus metrics (request_count, latency, cache hits)
- [ ] Expose /metrics в production configs
- [ ] Document tracing setup
- [ ] Include Grafana provisioning file

---

#### 12. Disaster recovery & backups (Phase 4.2) - Частично завершен
**Статус**: ⏳ Частично выполнено  
**Приоритет**: 🔵 Низкий

**Что сделано**:
- ✅ `backup/service.py` существует

**Что осталось**:
- [ ] AdvancedBackupManager с S3/Yandex storage
- [ ] AES-256 encryption
- [ ] Retention policy (7 daily/4 weekly/12 monthly)
- [ ] Checksum verification
- [ ] Automated restore tests
- [ ] Alerts
- [ ] Automate backup scheduling (systemd timers или k8s CronJob)
- [ ] Runbooks для backup creation/restoration
- [ ] Disaster scenarios runbooks
- [ ] Chaos testing plan (network partitions, node failure, load spikes)
- [ ] Simulated restore в CI/staging weekly

---

#### 13. High availability deployment (Phase 4.3) - Не начато
**Статус**: ⏳ Не начато  
**Приоритет**: 🔵 Низкий

**Что осталось**:
- [ ] Compose/Kubernetes manifests для:
  - Mongo replica set
  - Redis Sentinel
  - Qdrant clustering
  - API HPA (min 3 replicas, CPU 70%)
- [ ] Readiness/liveness probes
- [ ] Autoscaling behaviour
- [ ] Infra docs
- [ ] Load balancer instructions (nginx/traefik) с health checks
- [ ] Staging deployment verifying failover
- [ ] Load tests under failover

---

## 📊 Статистика оставшихся задач

### По фазам:
- **Phase 1 (Security)**: 9/9 ✅ (100%)
- **Phase 2 (Refactor & Performance)**: 
  - 2.1 (Break down app.py): ⏳ 10% (структура создана)
  - 2.2 (Performance): ✅ 100% (критичное выполнено)
  - 2.3 (Crawler robustness): ⏳ 50% (базовая функциональность есть)
  - 2.4 (Knowledge summary): ⏳ 30% (базовая функциональность есть)
- **Phase 3 (Testing & Quality)**:
  - 3.1 (Testing framework): ⏳ 80% (не хватает performance тестов)
  - 3.2 (CI/CD): ⏳ 85% (нужно увеличить coverage threshold)
  - 3.3 (QA import tests): ✅ 100%
  - 3.4 (Summary coverage): ⏳ 20% (2 теста из нужных)
- **Phase 4 (Infrastructure)**: ⏳ 10% (базовое есть)
- **Phase 5 (Documentation)**: ⏳ 50% (основное есть, нужно улучшить)

### По приоритетам:
- **🔴 Высокий приоритет**: 6 задач (блокируют полное завершение плана)
- **🟢 Средний приоритет**: 4 задачи (улучшения)
- **🔵 Низкий приоритет**: 3 задачи (опциональные улучшения)

**Итого оставшихся задач**: ~13 основных блоков работы

---

## 🎯 Рекомендации по приоритетам

### Немедленно (для полного завершения плана):
1. **Рефакторинг app.py** (Phase 2.1) - самая объемная задача
2. **Testing framework uplift** (Phase 3.1) - создать performance тесты, увеличить coverage
3. **CI/CD quality gates** (Phase 3.2) - увеличить coverage threshold до 90%

### В ближайшее время (улучшения):
4. **Knowledge summarisation upgrade** (Phase 2.4)
5. **Async crawler robustness** (Phase 2.3)
6. **Summary coverage** (Phase 3.4)

### Опционально (можно делать постепенно):
7. Developer tooling
8. Documentation system
9. Observability stack
10. Disaster recovery
11. High availability

---

## ✅ Вывод

**Критичные задачи для production**: ✅ **ВЫПОЛНЕНЫ (19/19)**

**Проект готов к production deployment** с текущим функционалом.

**Оставшиеся задачи** - это улучшения и полное завершение плана из TODO.md:
- Не блокируют deployment
- Можно делать постепенно
- Улучшают качество кода, покрытие тестами и документацию

**Статус проекта**: ✅ **PRODUCTION READY**  
**Статус плана TODO.md**: ⏳ **~60% завершено** (критичное - 100%, улучшения - частично)

---

*Обновлено: 2025-11-16*
