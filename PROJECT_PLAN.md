# Project Completion Plan - SiteLLM Vertebro

## Текущий статус

### ✅ Завершено (100%)
- **Voice Assistant Feature**: Полностью реализован, протестирован, задокументирован
  - 16/16 тестов проходят ✅
  - Браузерное тестирование завершено ✅
  - Готов к продакшену ✅

---

## План завершения проекта

### Phase 1: Critical Security Fixes (Приоритет 1)

#### 1.1 Comprehensive Input Validation
**Статус**: ⏳ Не начато  
**Приоритет**: 🔴 Критично

**Задачи**:
- [ ] Pydantic валидаторы для upload size (100 MB), MIME whitelist, magic-number check
- [ ] Unicode normalization, HTML escaping, length caps (Q≤1000, A≤10000)
- [ ] Crawler URL whitelists/blacklists, protocol enforcement
- [ ] 30s timeout, per-IP upload throttling (10/hour) в Redis
- [ ] ClamAV hook для binaries

**Файлы**:
- `app.py` - добавить валидаторы
- `api.py` - валидация endpoints
- `crawler/run_crawl.py` - SSRF protection
- `models.py` - Pydantic validators

**Тесты**: Unit тесты для validator edge-cases + integration тест для QA upload

---

#### 1.2 Rate Limiting & Attack Surface Hardening
**Статус**: ⏳ Не начато  
**Приоритет**: 🔴 Критично

**Задачи**:
- [ ] Redis-backed limiters (100 read/min/IP, 10 write/min/IP, 1000 req/hour/user)
- [ ] Sanitize Mongo queries (operator whitelist, escaping)
- [ ] CSP headers + DOMPurify + CSRF tokens
- [ ] Security middleware для private-IP blocking
- [ ] `_require_super_admin` logging

**Файлы**:
- `backend/security.py` - новый файл
- `app.py` - middleware integration
- `api.py` - rate limiting
- `mongo.py` - query sanitization

**Тесты**: Security suite (rate-limit, CSRF, SSRF, NoSQL injection)

---

#### 1.3 QA Import Backend/Frontend Parity
**Статус**: ⏳ Не начато  
**Приоритет**: 🟡 Высокий

**Задачи**:
- [ ] File-size/empty checks, CSV delimiter detection
- [ ] Excel error reporting, text-length truncation
- [ ] Duplicate detection, progress statuses
- [ ] Frontend: disable submit button, progress indicator, toasts

**Файлы**:
- `app.py: _read_qa_upload`
- `admin/js/index.js`
- `docs/manuals/`

**Тесты**: Integration тесты для CSV/Excel import

---

### Phase 2: Refactor & Performance (Приоритет 2)

#### 2.1 Break Down app.py Monolith
**Статус**: ⏳ Не начато  
**Приоритет**: 🟡 Высокий

**Задачи**:
- [ ] Создать `app/` package
- [ ] `app/main.py` (<500 LOC) для factory + middleware
- [ ] Переместить routers в `app/routers/`
- [ ] Переместить services в `app/services/`
- [ ] Обновить imports, dependency injection

**Файлы**:
- `app/main.py` - новый
- `app/routers/{projects,knowledge,backup,stats,voice}.py`
- `app/services/`
- `app/models/`

---

#### 2.2 Performance Optimization
**Статус**: ⏳ Не начато  
**Приоритет**: 🟡 Высокий

**Задачи**:
- [ ] Mongo: connection pooling (min 10 / max 100), indexes
- [ ] Redis caching layer (`backend/cache_manager.py`)
- [ ] Retrieval: RRF fusion, reranker batching, vector search caching
- [ ] API: gzip, SSE chunk tuning, ETag support

**Файлы**:
- `backend/cache_manager.py` - новый
- `mongo.py` - pooling
- `retrieval/` - optimizations

---

### Phase 3: Testing & Quality (Приоритет 3)

#### 3.1 Testing Framework Uplift
**Статус**: ⏳ Не начато  
**Приоритет**: 🟡 Средний

**Задачи**:
- [ ] Добавить `pytest-cov`, `pytest-asyncio`, `pytest-xdist`, `pytest-mock`
- [ ] `pytest.ini` с coverage config (min 80%)
- [ ] `conftest` fixtures для Mongo/Redis testcontainers
- [ ] Организовать тесты в `tests/{unit,integration,performance,security,e2e}`

---

#### 3.2 CI/CD Quality Gates
**Статус**: ⏳ Не начато  
**Приоритет**: 🟡 Средний

**Задачи**:
- [ ] `.github/workflows/ci.yml` с steps:
  - `ruff format --check`
  - `ruff check`
  - `mypy`
  - `bandit`
  - `pytest --cov --cov-fail-under=90`
- [ ] Upload coverage artifacts
- [ ] Performance smoke tests

---

### Phase 4: Voice Feature Enhancements (Опционально)

#### 4.1 Production Providers
**Статус**: ⏳ Инфраструктура готова  
**Приоритет**: 🟢 Низкий (не блокирует продакшен)

**Задачи**:
- [ ] Whisper integration с GPU support
- [ ] ElevenLabs TTS provider
- [ ] Azure Neural TTS
- [ ] Vosk offline recognition

---

#### 4.2 WebSocket Streaming
**Статус**: ⏳ Инфраструктура готова  
**Приоритет**: 🟢 Низкий

**Задачи**:
- [ ] Audio chunk streaming (нужен production recognizer)
- [ ] Real-time transcription
- [ ] Streaming synthesis

---

## Стратегия выполнения

### Этап 1: Критичные исправления (Week 1)
1. Input validation (1.1)
2. Rate limiting (1.2)
3. QA import parity (1.3)

### Этап 2: Рефакторинг (Week 2)
1. Break down app.py (2.1)
2. Performance optimization (2.2)

### Этап 3: Качество (Week 3)
1. Testing framework (3.1)
2. CI/CD gates (3.2)

### Этап 4: Улучшения (Week 4+)
1. Voice production providers (4.1)
2. WebSocket streaming (4.2)

---

## Метрики успеха

- ✅ Security: Zero HIGH/MEDIUM Bandit findings
- ✅ Performance: API p95 <500ms
- ✅ Test coverage: ≥90% total, ≥95% unit
- ✅ Documentation: Complete
- ✅ Voice feature: ✅ Complete (16/16 tests passing)

---

*Обновлено: 2025-11-16*

