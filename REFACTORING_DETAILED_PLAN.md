# Детальный план рефакторинга и завершения проекта

**Дата создания**: 2025-11-16  
**Статус**: В процессе выполнения

---

## ✅ Выполнено

### 1. Рефакторинг роутеров
- ✅ `app/services/auth.py` - AdminIdentity и auth helpers (~80 LOC)
- ✅ `app/routers/backup.py` - Backup endpoints (~200 LOC)
- ✅ `app/routers/stats.py` - Stats/logs/session endpoints (~200 LOC)
- ✅ `app/routers/admin.py` - Health/csrf/logout/sysinfo (~250 LOC)
- **Итого вынесено**: ~730 LOC из app.py

### 2. Тестирование и качество
- ✅ Coverage threshold увеличен до 90%
- ✅ Performance тесты созданы
- ✅ CI/CD улучшен
- ✅ Summary тесты расширены до 95%+ покрытия
- ✅ Crawler улучшен (retry logic, connection pooling)

---

## 📋 Осталось выполнить

### Phase 1: Улучшение knowledge/summary.py (приоритет: ВЫСОКИЙ)

**Цель**: Добавить batch calls, caching, metrics для оптимизации производительности

**Задачи**:
1. **Батчинг LLM вызовов**
   - Группировать несколько summary запросов в один batch
   - Использовать `asyncio.gather` для параллельных вызовов
   - Ограничение: batch size = 5-10 запросов

2. **Redis caching**
   - Кешировать результаты `generate_document_summary` (key: `summary:doc:{hash}`)
   - Кешировать результаты `generate_reading_segment_summary` (key: `summary:reading:{hash}`)
   - Кешировать результаты `generate_image_caption` (key: `summary:image:{hash}`)
   - TTL: 7 дней для summaries, 30 дней для captions
   - Использовать `backend.cache` для Redis доступа

3. **Metrics**
   - Логировать success/failure для каждого вызова
   - Измерять latency (время выполнения)
   - Отслеживать token usage (если доступно)
   - Использовать `observability.metrics` или structlog

**Оценка**: 2-3 часа работы

---

### Phase 2: Рефакторинг projects endpoints (приоритет: СРЕДНИЙ)

**Цель**: Вынести ~1500 LOC проектных endpoints в `app/routers/projects.py`

**Задачи**:
1. **Создать `app/routers/projects.py`**
   - GET `/api/v1/admin/projects` - список проектов
   - POST `/api/v1/admin/projects` - создать/обновить проект
   - GET `/api/v1/admin/projects/storage` - storage usage
   - GET `/api/v1/admin/projects/names` - список имен
   - GET `/api/v1/admin/projects/{project}/test` - тест проекта
   - DELETE `/api/v1/admin/projects/{name}` - удалить проект

2. **Telegram/Max/VK bot endpoints**
   - GET/POST `/api/v1/admin/projects/{project}/telegram/*`
   - GET/POST `/api/v1/admin/projects/{project}/max/*`
   - GET/POST `/api/v1/admin/projects/{project}/vk/*`

3. **Общие bot endpoints (legacy)**
   - GET/POST `/api/v1/admin/telegram/*`
   - GET/POST `/api/v1/admin/max/*`
   - GET/POST `/api/v1/admin/vk/*`

**Оценка**: 4-5 часов работы

---

### Phase 3: Рефакторинг knowledge endpoints (приоритет: СРЕДНИЙ)

**Цель**: Вынести ~2000 LOC knowledge endpoints в `app/routers/knowledge.py`

**Задачи**:
1. **Основные knowledge endpoints**
   - GET/POST `/api/v1/admin/knowledge`
   - PUT/DELETE `/api/v1/admin/knowledge/{id}`
   - GET `/api/v1/admin/knowledge/documents/{file_id}`

2. **Q&A endpoints**
   - GET/POST `/api/v1/admin/knowledge/qa`
   - PUT/DELETE `/api/v1/admin/knowledge/qa/{id}`
   - POST `/api/v1/admin/knowledge/qa/upload`
   - POST `/api/v1/admin/knowledge/qa/reorder`
   - POST `/api/v1/admin/knowledge/qa/unanswered/clear`

3. **Knowledge service endpoints**
   - GET/POST `/api/v1/admin/knowledge/service`
   - POST `/api/v1/admin/knowledge/service/run`
   - POST `/api/intelligent-processing/prompt`

**Оценка**: 5-6 часов работы

---

### Phase 4: LLM/Ollama endpoints (приоритет: НИЗКИЙ)

**Цель**: Вынести LLM и Ollama management в отдельный роутер

**Задачи**:
1. **LLM endpoints**
   - GET `/api/v1/admin/llm/models`
   - GET `/api/v1/admin/llm/availability`

2. **Ollama endpoints**
   - GET `/api/v1/admin/ollama/catalog`
   - GET/POST `/api/v1/admin/ollama/servers`
   - POST `/api/v1/admin/ollama/install`

**Оценка**: 2-3 часа работы

---

### Phase 5: Создание app/main.py factory (приоритет: ВЫСОКИЙ)

**Цель**: Создать factory для FastAPI app с middleware setup (<500 LOC)

**Задачи**:
1. **Создать `app/main.py`**
   - Функция `create_app() -> FastAPI`
   - Настройка middleware (CORS, Metrics, CSP, GZip, RateLimiting, CSRF, BasicAuth)
   - Регистрация роутеров
   - Монтирование static files
   - Lifespan management (возможно вынести в отдельный модуль)

2. **Обновить `app.py`**
   - Оставить только создание app через factory
   - Или полностью заменить на импорт из `app/main.py`

**Оценка**: 3-4 часа работы

---

### Phase 6: Backward compatibility (приоритет: ВЫСОКИЙ)

**Цель**: Обеспечить backward compatibility через `app/__init__.py`

**Задачи**:
1. **Обновить `app/__init__.py`**
   - Экспортировать `app` для `from app import app`
   - Экспортировать основные функции/классы для импорта

2. **Обновить imports**
   - Найти все `from app import ...` или `import app`
   - Убедиться, что они работают
   - Обновить при необходимости

**Оценка**: 2-3 часа работы

---

### Phase 7: Smoke tests (приоритет: СРЕДНИЙ)

**Цель**: Добавить базовые smoke tests для каждого роутера

**Задачи**:
1. **Создать `tests/test_routers_smoke.py`**
   - Тесты импорта каждого роутера
   - Тесты базовой регистрации роутера в app
   - Минимальные endpoint тесты (200 OK)

**Оценка**: 1-2 часа работы

---

## 🎯 Приоритизация и последовательность

### Неделя 1 (Текущая)
1. ✅ Phase 1: Улучшение knowledge/summary.py (НАЧАТО)
2. ✅ Phase 2: Рефакторинг projects (частично)
3. ✅ Phase 5: Создание app/main.py

### Неделя 2
4. Phase 3: Рефакторинг knowledge endpoints
5. Phase 4: LLM/Ollama endpoints
6. Phase 6: Backward compatibility
7. Phase 7: Smoke tests

---

## 📊 Метрики прогресса

**Текущий статус app.py**:
- Исходный размер: ~7101 LOC
- Вынесено: ~730 LOC (10%)
- Осталось: ~6370 LOC (90%)

**Целевой результат**:
- `app.py`: <1000 LOC (factory + legacy compatibility)
- `app/routers/*.py`: 200-500 LOC каждый
- `app/services/*.py`: 100-300 LOC каждый
- `app/main.py`: <500 LOC

---

## ⚠️ Риски и митигация

1. **Циклические зависимости**
   - Митигация: Использовать lazy imports, выносить общие функции в `app/services/`

2. **Большой размер endpoints**
   - Митигация: Разбивать на под-роутеры или отдельные файлы для больших групп

3. **Backward compatibility**
   - Митигация: Тщательное тестирование импортов, использование `app/__init__.py`

---

*План будет обновляться по мере выполнения задач*

