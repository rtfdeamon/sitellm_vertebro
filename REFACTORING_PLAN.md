# План рефакторинга app.py

**Файл**: `app.py`  
**Размер**: 7101 строка  
**Цель**: Разбить на модули <500 LOC каждый

---

## Структура после рефакторинга

```
app/
├── __init__.py          # Backward compatibility: expose app
├── main.py              # Factory + middleware (<500 LOC)
├── routers/
│   ├── __init__.py
│   ├── projects.py      # Projects endpoints (~1500 LOC)
│   ├── knowledge.py     # Knowledge endpoints (~2000 LOC)
│   ├── backup.py        # Backup endpoints (~400 LOC)
│   ├── stats.py         # Stats endpoints (~200 LOC)
│   └── admin.py         # Admin endpoints (~500 LOC)
├── services/
│   ├── __init__.py
│   ├── ollama.py        # Ollama management
│   ├── bots.py          # Telegram/Max/VK hubs
│   └── helpers.py       # Helper functions
└── models/
    ├── __init__.py
    └── schemas.py       # Pydantic models
```

---

## Группировка эндпоинтов

### app/main.py (<500 LOC)
- FastAPI factory
- Lifespan management
- Middleware setup
- Static files mounting
- Router registration

### app/routers/projects.py (~1500 LOC)
Группа: Проекты
- `GET /api/v1/admin/projects`
- `GET /api/v1/admin/projects/storage`
- `POST /api/v1/admin/projects`
- `DELETE /api/v1/admin/projects/{domain}`
- `POST /api/v1/admin/projects/prompt`
- `GET /api/v1/admin/projects/{domain}/test`
- `GET /api/v1/admin/projects/names`
- Проектные боты (Telegram/Max/VK) - отдельный роутер или подпапка

### app/routers/knowledge.py (~2000 LOC)
Группа: База знаний
- `GET /api/v1/admin/knowledge`
- `POST /api/v1/admin/knowledge`
- `POST /api/v1/admin/knowledge/upload`
- `POST /api/v1/admin/knowledge/deduplicate`
- `POST /api/v1/admin/knowledge/reindex`
- `DELETE /api/v1/admin/knowledge`
- `GET /api/v1/admin/knowledge/priority`
- `POST /api/v1/admin/knowledge/priority`
- `DELETE /api/v1/admin/knowledge/{file_id}`
- `GET /api/v1/admin/knowledge/documents/{file_id}`
- Q&A endpoints:
  - `GET /api/v1/admin/knowledge/qa`
  - `POST /api/v1/admin/knowledge/qa/upload`
  - `POST /api/v1/admin/knowledge/qa`
  - `PUT /api/v1/admin/knowledge/qa/{pair_id}`
  - `DELETE /api/v1/admin/knowledge/qa/{pair_id}`
  - `POST /api/v1/admin/knowledge/qa/reorder`
- Unanswered:
  - `GET /api/v1/admin/knowledge/unanswered`
  - `POST /api/v1/admin/knowledge/unanswered/clear`
  - `GET /api/v1/admin/knowledge/unanswered/export`
- Knowledge Service:
  - `GET /api/v1/admin/knowledge/service`
  - `POST /api/v1/admin/knowledge/service`
  - `POST /api/v1/admin/knowledge/service/run`

### app/routers/backup.py (~400 LOC)
Группа: Резервное копирование
- `GET /api/v1/backup/status`
- `POST /api/v1/backup/settings`
- `POST /api/v1/backup/run`
- `POST /api/v1/backup/restore`

### app/routers/stats.py (~200 LOC)
Группа: Статистика
- `GET /api/v1/admin/stats/requests`
- `GET /api/v1/admin/stats/requests/export`
- `GET /api/v1/admin/logs`
- `GET /api/v1/admin/session`

### app/routers/admin.py (~500 LOC)
Группа: Общие админ функции
- `GET /health`
- `GET /healthz`
- `GET /status`
- `GET /api/v1/admin/csrf-token`
- `GET /api/v1/admin/logout`
- `POST /api/v1/admin/logout`
- `GET /api/v1/admin/llm/models`
- `GET /api/v1/admin/llm/availability`
- `GET /api/v1/admin/ollama/catalog`
- `GET /api/v1/admin/ollama/servers`
- `POST /api/v1/admin/ollama/servers`
- `DELETE /api/v1/admin/ollama/servers/{name}`
- `POST /api/v1/admin/ollama/install`
- `POST /api/v1/feedback`
- `GET /api/v1/admin/feedback`
- `PATCH /api/v1/admin/feedback/{task_id}`
- `GET /api/v1/admin/telegram`
- `POST /api/v1/admin/telegram/config`
- `POST /api/v1/admin/telegram/start`
- `POST /api/v1/admin/telegram/stop`
- `GET /api/v1/admin/max`
- `POST /api/v1/admin/max/config`
- `POST /api/v1/admin/max/start`
- `POST /api/v1/admin/max/stop`
- `GET /api/v1/admin/vk`
- `POST /api/v1/admin/vk/config`
- `POST /api/v1/admin/vk/start`
- `POST /api/v1/admin/vk/stop`
- `POST /api/v1/desktop/build`
- `GET /sysinfo`

### app/services/
Вспомогательные сервисы:
- `ollama.py` - Ollama management functions
- `bots.py` - Telegram/Max/VK hub classes
- `helpers.py` - Helper functions (_normalize_project, _get_mongo_client, etc.)

### app/models/
- `schemas.py` - Все Pydantic модели из app.py

---

## Поэтапный план выполнения

### Этап 1: Подготовка структуры
1. ✅ Создать директории `app/routers/`, `app/services/`, `app/models/`
2. Создать `__init__.py` файлы
3. Вынести все Pydantic модели в `app/models/schemas.py`

### Этап 2: Вынос helper функций
1. Вынести helper функции в `app/services/helpers.py`
2. Обновить импорты

### Этап 3: Вынос сервисов
1. Вынести Ollama management в `app/services/ollama.py`
2. Вынести Bot hubs в `app/services/bots.py`

### Этап 4: Создание роутеров
1. Создать `app/routers/backup.py` (самый маленький)
2. Создать `app/routers/stats.py`
3. Создать `app/routers/admin.py`
4. Создать `app/routers/knowledge.py` (по частям)
5. Создать `app/routers/projects.py` (по частям)

### Этап 5: Создание main.py
1. Создать `app/main.py` с factory
2. Переместить lifespan management
3. Переместить middleware setup
4. Зарегистрировать все роутеры

### Этап 6: Обновление app/__init__.py
1. Обновить для backward compatibility
2. Expose `app` from `app.main`

### Этап 7: Тестирование
1. Обновить все импорты
2. Добавить smoke tests для каждого роутера
3. Запустить полный test suite

---

## Критерии успеха

- ✅ Каждый файл <500 LOC
- ✅ Все тесты проходят
- ✅ Backward compatibility сохранена
- ✅ Нет дублирования кода
- ✅ Imports работают корректно

---

*Обновлено: 2025-11-16*

