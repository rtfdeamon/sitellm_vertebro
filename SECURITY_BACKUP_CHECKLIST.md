# Чеклист исправления уязвимостей системы резервного копирования

**Дата создания:** 14 ноября 2024
**Последнее обновление:** 14 ноября 2024
**Версия:** 1.0
**Статус:** Готов к применению

---

## Содержание

1. [Pre-flight проверка](#pre-flight-проверка)
2. [Phase 1: КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ (P0)](#phase-1-критические-исправления-p0)
   - [PATCH 1: CSRF Protection](#patch-1-csrf-protection-4-часа)
   - [PATCH 2: Audit Logging](#patch-2-audit-logging-2-часа)
3. [Phase 2: ВАЖНЫЕ ИСПРАВЛЕНИЯ (P1)](#phase-2-важные-исправления-p1)
   - [PATCH 3: Path Validation](#patch-3-path-validation-3-часа)
   - [PATCH 4: Restore Confirmation](#patch-4-restore-confirmation-2-часа)
   - [PATCH 7: Error Sanitization](#patch-7-error-sanitization-1-час)
4. [Phase 3: ДОПОЛНИТЕЛЬНЫЕ УЛУЧШЕНИЯ (P2)](#phase-3-дополнительные-улучшения-p2)
   - [PATCH 5: Rate Limiting](#patch-5-rate-limiting-2-часа)
   - [PATCH 6: Security Headers](#patch-6-security-headers-1-час)
5. [Post-deployment проверки](#post-deployment-проверки)
6. [Rollback план (на случай проблем)](#rollback-план-на-случай-проблем)
7. [Документация изменений](#документация-изменений)
8. [Финальная проверка](#финальная-проверка)
9. [Контакты для эскалации](#контакты-для-эскалации)
10. [Метрики успеха](#метрики-успеха)

---

## Pre-flight проверка

- [ ] Создан backup текущей версии кода
- [ ] Создан backup текущей БД
- [ ] Есть доступ к production серверу
- [ ] Есть тестовое окружение для проверки
- [ ] Согласовано время технического окна (если требуется)

---

## Phase 1: КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ (P0)
**Срок: Сегодня (6 часов)**
**Риск downtime: Низкий (требуется restart приложения)**

### PATCH 1: CSRF Protection (4 часа)

#### Шаг 1.1: Добавить middleware класс
- [ ] Открыть файл `/Users/daniil/git/sitellm_vertebro/app.py`
- [ ] Найти класс `BasicAuthMiddleware` (~line 2558)
- [ ] После него добавить класс `CSRFProtectionMiddleware` из `SECURITY_BACKUP_FIXES.py`
- [ ] Проверить импорты:
  ```python
  from urllib.parse import urlparse
  import secrets
  ```

#### Шаг 1.2: Настроить environment переменные
- [ ] Создать/обновить файл `.env` или конфигурацию
- [ ] Добавить:
  ```bash
  # Разрешенные домены (через запятую)
  ALLOWED_ORIGINS=https://your-production-domain.com,https://www.your-domain.com
  ```
- [ ] Для локальной разработки:
  ```bash
  ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
  ```

#### Шаг 1.3: Применить middleware
- [ ] Найти место где добавляются middleware (~line 4900+)
- [ ] Добавить **ПОСЛЕ** `BasicAuthMiddleware`:
  ```python
  app.add_middleware(CSRFProtectionMiddleware)
  ```

#### Шаг 1.4: Обновить frontend (если нужно)
- [ ] Открыть `/Users/daniil/git/sitellm_vertebro/admin/js/backup.js`
- [ ] В функциях `handleBackupSettingsSave`, `handleBackupRun`, `handleBackupRestore`
- [ ] Проверить что fetch запросы включают:
  ```javascript
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',  // Для CSRF защиты
  }
  ```

#### Шаг 1.5: Тестирование
- [ ] Restart приложения
- [ ] **Test 1**: Запрос БЕЗ Origin (должен быть отклонен)
  ```bash
  curl -u "super:password" -X POST \
    http://localhost:8000/api/v1/backup/run \
    -H "Content-Type: application/json"
  # Ожидаем: HTTP 403
  ```
- [ ] **Test 2**: Запрос с правильным Origin (должен пройти)
  ```bash
  curl -u "super:password" -X POST \
    http://localhost:8000/api/v1/backup/run \
    -H "Content-Type: application/json" \
    -H "Origin: http://localhost:8000"
  # Ожидаем: HTTP 200 или 409
  ```
- [ ] **Test 3**: Через браузер UI должен работать нормально
- [ ] Проверить логи на отсутствие ошибок

---

### PATCH 2: Audit Logging (2 часа)

#### Шаг 2.1: Обновить функцию _require_super_admin
- [ ] Открыть файл `/Users/daniil/git/sitellm_vertebro/app.py`
- [ ] Найти функцию `_require_super_admin` (line 771)
- [ ] **ЗАМЕНИТЬ** существующую функцию на версию из `SECURITY_BACKUP_FIXES.py`
- [ ] Проверить что добавлены логи:
  - `logger.warning("unauthorized_super_admin_access_attempt", ...)`
  - `logger.info("super_admin_access_granted", ...)`

#### Шаг 2.2: Тестирование
- [ ] Restart приложения
- [ ] **Test 1**: Попытка доступа обычным админом
  ```bash
  # Создать обычного админа если нет
  curl -u "regular_admin:password" \
    http://localhost:8000/api/v1/backup/status
  # Ожидаем: HTTP 403
  ```
- [ ] Проверить лог файл:
  ```bash
  tail -f /var/log/sitellm/app.log | grep unauthorized_super_admin_access_attempt
  # Должно появиться:
  # {
  #   "event": "unauthorized_super_admin_access_attempt",
  #   "username": "regular_admin",
  #   "path": "/api/v1/backup/status",
  #   "ip": "127.0.0.1",
  #   ...
  # }
  ```
- [ ] **Test 2**: Успешный доступ супер-админом
  ```bash
  curl -u "super:password" \
    http://localhost:8000/api/v1/backup/status
  ```
- [ ] Проверить лог:
  ```bash
  tail -f /var/log/sitellm/app.log | grep super_admin_access_granted
  ```

#### Шаг 2.3: Настроить мониторинг (опционально, но рекомендуется)
- [ ] Если используется ELK/Grafana/etc:
  - [ ] Создать alert на `unauthorized_super_admin_access_attempt`
  - [ ] Threshold: 3+ попыток за 5 минут
  - [ ] Notification: Email/Slack админам
- [ ] Если нет системы мониторинга:
  - [ ] Настроить cron job для проверки логов:
    ```bash
    # /etc/cron.d/security-alerts
    */5 * * * * root grep unauthorized_super_admin_access_attempt /var/log/sitellm/app.log | tail -n 10 | mail -s "Security Alert" admin@example.com
    ```

---

## Phase 2: ВАЖНЫЕ ИСПРАВЛЕНИЯ (P1)
**Срок: На этой неделе (6 часов)**
**Риск downtime: Низкий**

### PATCH 3: Path Validation (3 часа)

#### Шаг 3.1: Создать модуль валидации
- [ ] Создать файл `/Users/daniil/git/sitellm_vertebro/backup/validators.py`
- [ ] Скопировать содержимое из `SECURITY_BACKUP_FIXES.py` (секция PATCH 3)
- [ ] Проверить импорты:
  ```python
  import re
  from pathlib import Path
  ```

#### Шаг 3.2: Обновить endpoint backup_restore
- [ ] Открыть файл `/Users/daniil/git/sitellm_vertebro/app.py`
- [ ] Найти функцию `backup_restore` (line 3517)
- [ ] Добавить импорт в начале файла:
  ```python
  from backup.validators import validate_remote_backup_path, BackupPathValidationError
  ```
- [ ] **ЗАМЕНИТЬ** существующий код валидации на код из `SECURITY_BACKUP_FIXES.py`

#### Шаг 3.3: Тестирование
- [ ] Restart приложения
- [ ] **Test 1**: Path traversal атака
  ```bash
  curl -u "super:password" -X POST \
    http://localhost:8000/api/v1/backup/restore \
    -H "Content-Type: application/json" \
    -H "Origin: http://localhost:8000" \
    -d '{"remotePath": "../../etc/passwd"}'
  # Ожидаем: HTTP 400, "remote_path_traversal_detected"
  ```
- [ ] **Test 2**: Путь вне разрешенной папки
  ```bash
  curl -u "super:password" -X POST \
    http://localhost:8000/api/v1/backup/restore \
    -H "Content-Type: application/json" \
    -H "Origin: http://localhost:8000" \
    -d '{"remotePath": "other-folder/backup.archive.gz"}'
  # Ожидаем: HTTP 400, "remote_path_must_be_in_folder"
  ```
- [ ] **Test 3**: Валидный путь
  ```bash
  curl -u "super:password" -X POST \
    http://localhost:8000/api/v1/backup/restore \
    -H "Content-Type: application/json" \
    -H "Origin: http://localhost:8000" \
    -d '{"remotePath": "sitellm-backups/test-backup.archive.gz"}'
  # Ожидаем: HTTP 200 или другая бизнес ошибка (не валидации)
  ```
- [ ] **Test 4**: Null byte injection
  ```bash
  curl -u "super:password" -X POST \
    http://localhost:8000/api/v1/backup/restore \
    -H "Content-Type: application/json" \
    -H "Origin: http://localhost:8000" \
    -d '{"remotePath": "sitellm-backups/backup.archive.gz\u0000../../etc/passwd"}'
  # Ожидаем: HTTP 400, "remote_path_contains_null_byte"
  ```

---

### PATCH 4: Restore Confirmation (2 часа)

#### Шаг 4.1: Обновить frontend
- [ ] Открыть файл `/Users/daniil/git/sitellm_vertebro/admin/js/backup.js`
- [ ] Найти функцию `handleBackupRestore` (line 419)
- [ ] **ЗАМЕНИТЬ** существующую функцию на версию из `SECURITY_BACKUP_FIXES.py`

#### Шаг 4.2: Обновить backend
- [ ] Открыть файл `/Users/daniil/git/sitellm_vertebro/app.py`
- [ ] В функции `backup_restore` (после валидации пути)
- [ ] Добавить проверку заголовка:
  ```python
  # Require explicit confirmation
  confirmation_header = request.headers.get("X-Confirmation")
  if confirmation_header != "restore-confirmed":
      logger.warning(
          "backup_restore_missing_confirmation",
          username=identity.username,
          path=remote_path,
      )
      raise HTTPException(
          status_code=400,
          detail="restore_operation_requires_explicit_confirmation"
      )
  ```

#### Шаг 4.3: Тестирование
- [ ] Restart приложения
- [ ] **Test 1**: Попытка restore без заголовка подтверждения
  ```bash
  curl -u "super:password" -X POST \
    http://localhost:8000/api/v1/backup/restore \
    -H "Content-Type: application/json" \
    -H "Origin: http://localhost:8000" \
    -d '{"remotePath": "sitellm-backups/test.archive.gz"}'
  # Ожидаем: HTTP 400, "restore_operation_requires_explicit_confirmation"
  ```
- [ ] **Test 2**: Через UI
  - [ ] Открыть браузер, зайти в админ панель
  - [ ] Нажать кнопку "Restore"
  - [ ] Должно появиться **два** подтверждения:
    - Первое: confirm() с предупреждением
    - Второе: prompt() с требованием ввести "RESTORE DATABASE"
  - [ ] Проверить что при отмене любого из них, restore не выполняется
  - [ ] Проверить что при полном подтверждении, restore выполняется

---

### PATCH 7: Error Sanitization (1 час)

#### Шаг 7.1: Добавить функцию sanitization
- [ ] Открыть файл `/Users/daniil/git/sitellm_vertebro/backup/service.py`
- [ ] В начале файла (после импортов) добавить функцию `sanitize_error_message` из `SECURITY_BACKUP_FIXES.py`

#### Шаг 7.2: Применить sanitization к ошибкам
- [ ] В функции `perform_backup` (line 168-170)
- [ ] Обернуть сообщения об ошибках:
  ```python
  raise BackupError(sanitize_error_message(error_msg)) from exc
  ```
- [ ] Повторить для функции `perform_restore` (line 257-259)
- [ ] Повторить для `_download_archive` (line 199-200)

#### Шаг 7.3: Тестирование
- [ ] Создать условие ошибки (например, неправильный путь к mongodump)
- [ ] Проверить что в production (`DEBUG=false`) ошибка показывает только тип:
  ```
  "error": "mongodump_failed"  # Без деталей
  ```
- [ ] Проверить что в debug (`DEBUG=true`) ошибка показывает детали:
  ```
  "error": "mongodump_failed: /path/to/file not found"
  ```

---

## Phase 3: ДОПОЛНИТЕЛЬНЫЕ УЛУЧШЕНИЯ (P2)
**Срок: Следующий спринт (3 часа)**
**Риск downtime: Низкий**

### PATCH 5: Rate Limiting (2 часа)

#### Шаг 5.1: Установить зависимости
- [ ] Добавить в `requirements.txt`:
  ```
  slowapi==0.1.9
  ```
- [ ] Установить:
  ```bash
  pip install slowapi==0.1.9
  ```

#### Шаг 5.2: Инициализировать limiter
- [ ] Открыть файл `/Users/daniil/git/sitellm_vertebro/app.py`
- [ ] Добавить импорты:
  ```python
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  from slowapi.errors import RateLimitExceeded
  ```
- [ ] После создания `app = FastAPI(...)` добавить:
  ```python
  limiter = Limiter(
      key_func=get_remote_address,
      default_limits=["100/hour"],
      storage_uri=os.getenv("REDIS_URL", "memory://"),
  )
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
  ```

#### Шаг 5.3: Применить к эндпоинтам
- [ ] Добавить декораторы:
  ```python
  @app.get("/api/v1/backup/status", ...)
  @limiter.limit("30/minute")
  async def backup_status(...):

  @app.post("/api/v1/backup/run", ...)
  @limiter.limit("5/hour")
  async def backup_run(...):

  @app.post("/api/v1/backup/restore", ...)
  @limiter.limit("2/hour")
  async def backup_restore(...):
  ```

#### Шаг 5.4: Тестирование
- [ ] Restart приложения
- [ ] **Test**: Отправить 6 запросов на `/api/v1/backup/run` за минуту
  ```bash
  for i in {1..6}; do
    curl -u "super:password" -X POST \
      http://localhost:8000/api/v1/backup/run \
      -H "Origin: http://localhost:8000"
    sleep 1
  done
  # Первые 5 должны пройти (или вернуть 409)
  # 6-й должен вернуть HTTP 429 Too Many Requests
  ```

---

### PATCH 6: Security Headers (1 час)

#### Шаг 6.1: Добавить middleware
- [ ] Открыть файл `/Users/daniil/git/sitellm_vertebro/app.py`
- [ ] После `CSRFProtectionMiddleware` добавить класс `SecurityHeadersMiddleware` из `SECURITY_BACKUP_FIXES.py`

#### Шаг 6.2: Применить middleware
- [ ] Добавить:
  ```python
  DEBUG = os.getenv("DEBUG", "false").lower() == "true"
  app.add_middleware(SecurityHeadersMiddleware, debug=DEBUG)
  ```

#### Шаг 6.3: Тестирование
- [ ] Restart приложения
- [ ] Проверить заголовки:
  ```bash
  curl -I http://localhost:8000/admin
  # Должны быть заголовки:
  # X-Frame-Options: DENY
  # X-Content-Type-Options: nosniff
  # Content-Security-Policy: ...
  # Referrer-Policy: strict-origin-when-cross-origin
  ```

---

## Post-deployment проверки

### Функциональные тесты
- [ ] **Test 1**: Супер-админ может создать backup
  - [ ] Зайти в UI под супер-админом
  - [ ] Нажать "Run Backup"
  - [ ] Проверить что job создался и выполнился

- [ ] **Test 2**: Супер-админ может восстановить backup
  - [ ] Выбрать backup из списка
  - [ ] Нажать "Use for restore"
  - [ ] Подтвердить двойное подтверждение
  - [ ] Проверить что restore выполнился (в тестовом окружении!)

- [ ] **Test 3**: Обычный админ НЕ видит раздел backup
  - [ ] Зайти под обычным админом
  - [ ] Проверить что раздел "Backup" скрыт

- [ ] **Test 4**: Обычный админ НЕ может вызвать API
  - [ ] Попытка через curl с credentials обычного админа
  - [ ] Должен вернуть HTTP 403
  - [ ] Должно появиться в логах

### Security тесты
- [ ] **Test 5**: CSRF защита работает
  - [ ] Создать тестовый HTML с CSRF атакой
  - [ ] Открыть в браузере где авторизован супер-админ
  - [ ] Проверить что атака заблокирована

- [ ] **Test 6**: Path validation работает
  - [ ] Попробовать path traversal через API
  - [ ] Должен вернуть HTTP 400

- [ ] **Test 7**: Rate limiting работает
  - [ ] Отправить много запросов быстро
  - [ ] Должен вернуть HTTP 429

### Мониторинг
- [ ] Проверить что логи пишутся корректно
- [ ] Проверить что alerts настроены (если применимо)
- [ ] Проверить что metrics собираются (если применимо)

---

## Rollback план (на случай проблем)

### Если что-то пошло не так

#### Откат PATCH 1 (CSRF Protection)
```bash
# 1. Удалить CSRFProtectionMiddleware из app.py
# 2. Удалить app.add_middleware(CSRFProtectionMiddleware)
# 3. Restart приложения
```

#### Откат PATCH 2 (Audit Logging)
```bash
# 1. Восстановить старую версию _require_super_admin
# 2. Убрать логирование
# 3. Restart приложения
```

#### Откат PATCH 3 (Path Validation)
```bash
# 1. Удалить импорт validate_remote_backup_path
# 2. Восстановить старый код валидации в backup_restore
# 3. Restart приложения
```

#### Откат PATCH 4 (Restore Confirmation)
```bash
# 1. Восстановить старую версию handleBackupRestore в backup.js
# 2. Убрать проверку X-Confirmation из backend
# 3. Очистить кеш браузера
```

#### Полный откат
```bash
# Если всё сломалось:
git checkout HEAD~1  # Откат к предыдущему коммиту
systemctl restart sitellm
```

---

## Документация изменений

### После успешного применения

- [ ] Обновить CHANGELOG.md:
  ```markdown
  ## [Security Hardening] 2025-11-14

  ### Security
  - Added CSRF protection for backup endpoints
  - Added audit logging for all super admin access attempts
  - Added path validation for backup restore operations
  - Added double confirmation for dangerous restore operations
  - Added rate limiting for backup endpoints
  - Added security headers (CSP, X-Frame-Options, etc)
  - Sanitized error messages to prevent information leakage
  ```

- [ ] Обновить README.md (если есть раздел Security)

- [ ] Создать runbook для реагирования на security incidents

- [ ] Провести security training для команды

---

## Финальная проверка

### Pre-production checklist
- [ ] Все тесты пройдены успешно
- [ ] Код ревью выполнено
- [ ] Security ревью выполнено
- [ ] Performance тесты пройдены
- [ ] Backup создан
- [ ] Rollback план готов
- [ ] Monitoring настроен
- [ ] Alerts настроены
- [ ] Документация обновлена

### Production deployment
- [ ] Scheduled maintenance window (если нужно)
- [ ] Уведомить пользователей (если нужно)
- [ ] Deploy на production
- [ ] Smoke tests после deploy
- [ ] Мониторинг в течение 24 часов
- [ ] Post-mortem meeting

---

## Контакты для эскалации

**При обнаружении проблем:**

1. **Первый уровень**: Backend developer (вы)
2. **Второй уровень**: Tech Lead / CTO
3. **Экстренная ситуация**: Rollback + post-mortem

**Логи и мониторинг:**
- Application logs: `/var/log/sitellm/app.log`
- Error logs: `/var/log/sitellm/error.log`
- Security events: Искать по ключевым словам:
  - `unauthorized_super_admin_access_attempt`
  - `csrf_validation_failed`
  - `backup_restore_invalid_path`

---

## Метрики успеха

**После применения патчей должно быть:**

✅ **0** случаев успешной CSRF атаки
✅ **100%** логирование попыток доступа
✅ **0** успешных path traversal атак
✅ **0** случайных restore без подтверждения
✅ **<0.1%** ложных срабатываний CSRF защиты

**Время на применение всех патчей: ~15 часов**

```
P0 (критичные):      6 часов  ████████████░░░░░░░░
P1 (важные):         6 часов  ████████████░░░░░░░░
P2 (дополнительные): 3 часа   ██████░░░░░░░░░░░░░░
                    ─────────
                     15 часов ИТОГО
```

---

## Связанные документы

**Документация по безопасности резервного копирования:**
- `SECURITY_BACKUP_ACCESS_CONTROL.md` - Контроль доступа
- `SECURITY_BACKUP_SUMMARY.md` - Краткая сводка по безопасности
- `SECURITY_BACKUP_ANALYSIS.md` - Детальный анализ безопасности
- `SECURITY_BACKUP_ATTACK_SCENARIOS.md` - Сценарии атак
- `SECURITY_BACKUP_CHECKLIST.md` - Чеклист исправлений (этот документ)

**Дата анализа:** 14 ноября 2024
**Автор:** Backend Security Coding Expert
**Статус:** Готов к применению
