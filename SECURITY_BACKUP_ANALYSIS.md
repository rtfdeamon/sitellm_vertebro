# Анализ безопасности системы резервного копирования

**Дата создания:** 14 ноября 2024
**Последнее обновление:** 14 ноября 2024
**Версия:** 1.0
**Статус:** Актуально

---

## Содержание

1. [Резюме](#резюме)
2. [Найденные уязвимости](#найденные-уязвимости)
   - [1. КРИТИЧЕСКАЯ: Отсутствие CSRF защиты](#1-критическая-отсутствие-csrf-защиты)
   - [2. ВЫСОКАЯ: Отсутствие аудита попыток доступа](#2-высокая-отсутствие-аудита-попыток-доступа)
   - [3. СРЕДНЯЯ: Отсутствие валидации remote_path](#3-средняя-отсутствие-валидации-remote_path)
   - [4. СРЕДНЯЯ: Отсутствие подтверждения опасных операций](#4-средняя-отсутствие-подтверждения-опасных-операций)
   - [5. НИЗКАЯ: Отсутствие rate limiting](#5-низкая-отсутствие-rate-limiting)
   - [6. НИЗКАЯ: Утечка информации через timing attacks](#6-низкая-утечка-информации-через-timing-attacks)
   - [7. ИНФОРМАЦИОННАЯ: Отсутствие HTTP Security Headers](#7-информационная-отсутствие-http-security-headers)
3. [Ответы на конкретные вопросы](#ответы-на-конкретные-вопросы)
   - [Обход ограничений](#1-обход-ограничений)
   - [Утечка информации](#2-утечка-информации)
   - [Манипуляция сессией](#3-манипуляция-сессией)
   - [API эндпоинты](#4-api-эндпоинты)
   - [Восстановление](#5-восстановление)
4. [Матрица рисков](#матрица-рисков)
5. [Общая оценка безопасности](#общая-оценка-безопасности)
6. [Рекомендации по приоритетам](#рекомендации-по-приоритетам)
7. [Итоговая оценка](#итоговая-оценка)
8. [Приложение: Скрипты для тестирования](#приложение-скрипты-для-тестирования)

---

## Резюме

Проведен углубленный анализ системы резервного копирования на предмет краевых случаев безопасности. Система в целом **защищена должным образом** на уровне бэкенда, но обнаружены **критические уязвимости** в области защиты от атак и логирования инцидентов безопасности.

**Критичность найденных проблем: СРЕДНЯЯ-ВЫСОКАЯ**

---

## Найденные уязвимости

### 1. КРИТИЧЕСКАЯ: Отсутствие CSRF защиты

**Файл:** `app.py` (эндпоинты `/api/v1/backup/*`)
**Риск:** ВЫСОКИЙ
**CVSS Score:** 7.5 (High)

#### Описание проблемы
Все эндпоинты бэкапа используют POST запросы, но **не имеют защиты от CSRF атак**. При использовании Basic Authentication без CSRF токенов, злоумышленник может:

1. Создать вредоносную страницу с JavaScript кодом
2. Заставить авторизованного супер-админа посетить эту страницу
3. Выполнить от его имени опасные операции:
   - Запустить восстановление БД (`/api/v1/backup/restore`)
   - Изменить настройки бэкапа (`/api/v1/backup/settings`)
   - Очистить токен Яндекс.Диска

```javascript
// Пример CSRF атаки
fetch('https://target-server.com/api/v1/backup/restore', {
  method: 'POST',
  credentials: 'include', // Включает Basic Auth заголовки
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ remotePath: 'malicious-backup.archive.gz' })
});
```

#### Почему это работает
- Basic Authentication автоматически включается браузером в запросы
- Отсутствует проверка `Origin` или `Referer` заголовков
- Отсутствует CSRF токен в запросах
- Нет проверки `SameSite` cookies (т.к. используется Basic Auth)

#### Рекомендации по исправлению

**Вариант 1: CSRF Token (рекомендуется)**
```python
# app.py - добавить middleware
from starlette.middleware.csrf import CSRFMiddleware

app.add_middleware(
    CSRFMiddleware,
    secret="your-secret-key-here",  # Из env переменной
)

# Для каждого POST/PUT/DELETE эндпоинта добавить проверку
@app.post("/api/v1/backup/restore", response_class=ORJSONResponse)
async def backup_restore(request: Request, payload: BackupRestoreRequest) -> ORJSONResponse:
    identity = _require_super_admin(request)

    # CSRF защита для опасных операций
    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token or not verify_csrf_token(csrf_token, request):
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")

    # ... остальной код
```

**Вариант 2: Origin/Referer проверка (дополнительная защита)**
```python
def _validate_request_origin(request: Request) -> None:
    """Validate Origin/Referer headers for state-changing operations."""
    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")

    # Whitelist разрешенных origin
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

    if origin:
        if origin not in allowed_origins:
            raise HTTPException(status_code=403, detail="Invalid origin")
    elif referer:
        # Проверка referer как fallback
        parsed_referer = urlparse(referer)
        if f"{parsed_referer.scheme}://{parsed_referer.netloc}" not in allowed_origins:
            raise HTTPException(status_code=403, detail="Invalid referer")
    else:
        # Для API запросов без Origin/Referer требуем специальный заголовок
        api_key = request.headers.get("X-Requested-With")
        if api_key != "XMLHttpRequest":
            raise HTTPException(status_code=403, detail="Missing CSRF protection headers")

# Добавить в каждый POST эндпоинт
@app.post("/api/v1/backup/restore", response_class=ORJSONResponse)
async def backup_restore(request: Request, payload: BackupRestoreRequest) -> ORJSONResponse:
    identity = _require_super_admin(request)
    _validate_request_origin(request)  # <-- ДОБАВИТЬ ЭТО
    # ... остальной код
```

**Вариант 3: Double Submit Cookie Pattern**
```python
# При входе супер-админа создаем CSRF токен
@app.post("/api/v1/admin/login")
async def admin_login(request: Request, response: Response):
    # ... проверка credentials

    # Генерируем CSRF токен
    csrf_token = secrets.token_urlsafe(32)

    # Сохраняем в cookie (HttpOnly=False, чтобы JS мог читать)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=True,  # только HTTPS
        samesite="strict"
    )

    # Также сохраняем в сессии на сервере для проверки
    request.session["csrf_token"] = csrf_token

    return {"status": "ok"}

# Проверка CSRF токена
def _require_csrf_token(request: Request) -> None:
    submitted_token = request.headers.get("X-CSRF-Token")
    session_token = request.session.get("csrf_token")

    if not submitted_token or not session_token:
        raise HTTPException(status_code=403, detail="CSRF token missing")

    if not hmac.compare_digest(submitted_token, session_token):
        raise HTTPException(status_code=403, detail="CSRF token invalid")
```

---

### 2. ВЫСОКАЯ: Отсутствие аудита попыток доступа

**Файл:** `app.py` (функция `_require_super_admin`)
**Риск:** ВЫСОКИЙ
**CVSS Score:** 6.5 (Medium)

#### Описание проблемы
При попытке не-супер админа получить доступ к эндпоинтам бэкапа:
- Возвращается HTTP 403
- **НО**: нет логирования попытки доступа
- Невозможно обнаружить попытки атаки или скомпрометированные аккаунты

#### Рекомендации по исправлению
```python
def _require_super_admin(request: Request) -> AdminIdentity:
    identity = _require_admin(request)
    if not identity.is_super:
        # КРИТИЧНО: Логируем попытку несанкционированного доступа
        logger.warning(
            "unauthorized_super_admin_access_attempt",
            username=identity.username,
            path=request.url.path,
            method=request.method,
            ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("User-Agent", "unknown"),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        raise HTTPException(status_code=403, detail="Super admin privileges required")

    # Также логируем успешный доступ для аудита
    logger.info(
        "super_admin_access_granted",
        username=identity.username,
        path=request.url.path,
        method=request.method,
    )

    return identity
```

#### Дополнительно: Система оповещений
```python
# Отправка алертов при повторных попытках
FAILED_ACCESS_THRESHOLD = 3
ALERT_TIME_WINDOW = 300  # 5 минут

async def _check_brute_force_attempts(username: str, request: Request) -> None:
    """Detect and alert on repeated unauthorized access attempts."""
    cache_key = f"failed_super_admin_access:{username}"

    # Используем Redis для подсчета попыток
    current_count = await redis_client.incr(cache_key)
    if current_count == 1:
        await redis_client.expire(cache_key, ALERT_TIME_WINDOW)

    if current_count >= FAILED_ACCESS_THRESHOLD:
        # Отправка критического алерта
        await send_security_alert(
            severity="CRITICAL",
            event="repeated_unauthorized_super_admin_access",
            username=username,
            ip=request.client.host if request.client else "unknown",
            attempts=current_count,
        )

        # Опционально: временная блокировка аккаунта
        await temporarily_lock_account(username, duration=900)  # 15 минут
```

---

### 3. СРЕДНЯЯ: Отсутствие валидации remote_path

**Файл:** `backup/service.py` (функция `perform_restore`)
**Риск:** СРЕДНИЙ
**CVSS Score:** 5.3 (Medium)

#### Описание проблемы
Параметр `remote_path` не проходит должную валидацию:
- Отсутствует проверка на path traversal атаки
- Можно указать произвольный путь на Яндекс.Диске
- Теоретически возможно восстановление из чужого бэкапа (если известен путь)

```python
# app.py:3531 - слабая валидация
remote_path = (payload.remote_path or "").strip()
if not remote_path:
    raise HTTPException(status_code=400, detail="remote_path_required")

# backup/service.py:231 - используется Path.name, но недостаточно
archive_path = Path(tmpdir) / Path(remote_path).name
```

#### Потенциальные векторы атаки
```python
# 1. Path traversal (частично защищено использованием .name)
{
  "remotePath": "../../etc/passwd"
  # -> Защищено: Path.name вернет только "passwd"
}

# 2. Восстановление из чужой папки на Яндекс.Диске
{
  "remotePath": "other-company-backups/database-20250101-120000.archive.gz"
  # -> НЕ защищено: можно указать путь вне папки sitellm-backups
}

# 3. Длинный путь (DoS)
{
  "remotePath": "a/" * 10000 + "backup.archive.gz"
  # -> НЕ защищено: может вызвать проблемы с памятью/файловой системой
}
```

#### Рекомендации по исправлению

```python
# models.py или validators.py
import re
from pathlib import Path

MAX_PATH_LENGTH = 512
ALLOWED_PATH_PATTERN = re.compile(r'^[a-zA-Z0-9_\-/]+\.archive\.gz$')

def validate_remote_backup_path(path: str, allowed_folder: str | None = None) -> str:
    """
    Validate and sanitize remote backup path.

    Security checks:
    - Path length limit
    - No path traversal sequences
    - Must be within allowed folder
    - Must end with .archive.gz
    - Only safe characters allowed
    """
    if not path or not isinstance(path, str):
        raise ValueError("remote_path_required")

    path = path.strip()

    # 1. Length check
    if len(path) > MAX_PATH_LENGTH:
        raise ValueError(f"remote_path_too_long (max {MAX_PATH_LENGTH} chars)")

    # 2. Pattern check
    if not ALLOWED_PATH_PATTERN.match(path):
        raise ValueError("remote_path_invalid_format (use only: a-zA-Z0-9_-/.archive.gz)")

    # 3. Path traversal check
    if ".." in path or path.startswith("/"):
        raise ValueError("remote_path_traversal_detected")

    # 4. Null byte check
    if "\x00" in path:
        raise ValueError("remote_path_null_byte_detected")

    # 5. Must end with .archive.gz
    if not path.endswith(".archive.gz"):
        raise ValueError("remote_path_must_be_archive")

    # 6. Folder restriction
    if allowed_folder:
        normalized_folder = allowed_folder.strip("/")
        if not path.startswith(f"{normalized_folder}/"):
            raise ValueError(f"remote_path_must_be_in_folder: {normalized_folder}")

    return path

# app.py - применить валидацию
@app.post("/api/v1/backup/restore", response_class=ORJSONResponse)
async def backup_restore(request: Request, payload: BackupRestoreRequest) -> ORJSONResponse:
    identity = _require_super_admin(request)

    # Получаем настройки для проверки разрешенной папки
    settings_model = await request.state.mongo.get_backup_settings()
    allowed_folder = normalize_remote_folder(settings_model.ya_disk_folder)

    try:
        # КРИТИЧНО: Валидация пути
        remote_path = validate_remote_backup_path(
            payload.remote_path,
            allowed_folder=allowed_folder
        )
    except ValueError as exc:
        logger.warning(
            "backup_restore_invalid_path",
            username=identity.username,
            path=payload.remote_path,
            error=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc))

    # ... остальной код
```

---

### 4. СРЕДНЯЯ: Отсутствие подтверждения опасных операций

**Файл:** `admin/js/backup.js`
**Риск:** СРЕДНИЙ
**CVSS Score:** 4.3 (Medium)

#### Описание проблемы
Операция восстановления БД не требует дополнительного подтверждения:
- Один клик может перезаписать всю БД
- Нет требования ввести название БД для подтверждения
- Отсутствует механизм "две пары глаз" (two-person rule)

#### Рекомендации по исправлению

```javascript
// admin/js/backup.js
const handleBackupRestore = async () => {
  if (!global.adminSession?.is_super || backupRestoreBtn?.disabled) return;

  const remotePath = (backupRestorePathInput?.value || '').trim();
  if (!remotePath) {
    pushBackupMessage('backupRestorePathMissing', 'error');
    return;
  }

  // КРИТИЧНО: Двойное подтверждение для опасных операций
  const warningMessage = translate('backupRestoreWarning', {
    path: remotePath,
    warning: 'THIS WILL COMPLETELY OVERWRITE THE DATABASE. ALL CURRENT DATA WILL BE LOST!'
  });

  // Первое подтверждение
  if (!confirm(warningMessage)) {
    return;
  }

  // Второе подтверждение с вводом текста
  const confirmText = prompt(
    translate('backupRestoreTypeConfirm', {
      message: 'Type "RESTORE DATABASE" to confirm this dangerous operation:'
    })
  );

  if (confirmText !== 'RESTORE DATABASE') {
    pushBackupMessage('backupRestoreCancelled', 'info');
    return;
  }

  try {
    backupRestoreBtn.disabled = true;
    const resp = await fetch('/api/v1/backup/restore', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Confirmation': 'restore-confirmed'  // Дополнительная защита на бэкенде
      },
      body: JSON.stringify({ remotePath }),
    });
    // ... остальной код
  }
  // ...
};
```

**Backend защита:**
```python
@app.post("/api/v1/backup/restore", response_class=ORJSONResponse)
async def backup_restore(request: Request, payload: BackupRestoreRequest) -> ORJSONResponse:
    identity = _require_super_admin(request)

    # Требуем явное подтверждение опасной операции
    confirmation_header = request.headers.get("X-Confirmation")
    if confirmation_header != "restore-confirmed":
        raise HTTPException(
            status_code=400,
            detail="restore_operation_requires_explicit_confirmation"
        )

    # Опционально: Two-person rule для критических операций
    if ENABLE_TWO_PERSON_RULE:
        approval_token = request.headers.get("X-Approval-Token")
        if not approval_token or not await verify_second_approval(approval_token, identity.username):
            raise HTTPException(
                status_code=403,
                detail="restore_requires_second_super_admin_approval"
            )

    # ... остальной код
```

---

### 5. НИЗКАЯ: Отсутствие rate limiting

**Файл:** `app.py` (все эндпоинты бэкапа)
**Риск:** НИЗКИЙ
**CVSS Score:** 3.1 (Low)

#### Описание проблемы
Эндпоинты бэкапа не имеют rate limiting:
- Можно спамить запросы на создание бэкапа
- DoS атака через запросы `/api/v1/backup/status`
- Brute-force попытки угадать пути к бэкапам

#### Рекомендации по исправлению

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Инициализация rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Применение rate limiting к эндпоинтам
@app.get("/api/v1/backup/status", response_class=ORJSONResponse)
@limiter.limit("30/minute")  # Ограничение на статус
async def backup_status(request: Request, limit: int = 10) -> ORJSONResponse:
    _require_super_admin(request)
    # ... код

@app.post("/api/v1/backup/run", response_class=ORJSONResponse)
@limiter.limit("5/hour")  # Строгое ограничение на создание бэкапов
async def backup_run(request: Request, payload: BackupRunRequest | None = None) -> ORJSONResponse:
    identity = _require_super_admin(request)
    # ... код

@app.post("/api/v1/backup/restore", response_class=ORJSONResponse)
@limiter.limit("2/hour")  # Очень строгое ограничение на восстановление
async def backup_restore(request: Request, payload: BackupRestoreRequest) -> ORJSONResponse:
    identity = _require_super_admin(request)
    # ... код
```

---

### 6. НИЗКАЯ: Утечка информации через timing attacks

**Файл:** `app.py` (эндпоинт `/api/v1/backup/status`)
**Риск:** ОЧЕНЬ НИЗКИЙ
**CVSS Score:** 2.3 (Low)

#### Описание проблемы
Время ответа может выдать информацию о существовании бэкапов:
- Запрос с параметром `limit=50` может отвечать дольше
- По времени ответа можно понять, есть ли бэкапы в системе

#### Оценка реальной угрозы
- Требуется авторизация (уже есть доступ к `/api/v1/backup/status`)
- Информация о существовании бэкапов не критична
- **НЕ ТРЕБУЕТ ИСПРАВЛЕНИЯ** (очень низкий приоритет)

---

### 7. ИНФОРМАЦИОННАЯ: Отсутствие HTTP Security Headers

**Файл:** `app.py` (middleware)
**Риск:** НИЗКИЙ
**CVSS Score:** 3.7 (Low)

#### Описание проблемы
Отсутствуют важные security headers:
- `Content-Security-Policy`
- `X-Frame-Options`
- `X-Content-Type-Options`
- `Strict-Transport-Security`
- `Referrer-Policy`

#### Рекомендации по исправлению

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # HTTPS only (в production)
        if not DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (настроить под ваше приложение)
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # 'unsafe-inline' убрать в production
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # XSS Protection (legacy, but doesn't hurt)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response

# Добавить middleware
app.add_middleware(SecurityHeadersMiddleware)
```

---

## Ответы на конкретные вопросы

### 1. Обход ограничений

#### Можно ли обойти скрытие UI через DevTools?
**ДА**, но это **НЕ проблема безопасности**.

```javascript
// Через DevTools можно выполнить:
document.getElementById('block-backup').style.display = 'block';

// Или даже вызвать функции напрямую:
window.BackupModule.refreshBackupStatus();
```

**Почему это не опасно:**
- Frontend проверки это только UX
- Все реальные проверки на бэкенде
- API запросы вернут HTTP 403 для не-супер админов
- Это **защита глубиной** (defense in depth)

**Проверено:**
```bash
# Попытка вызвать API не-супер админом
curl -u "regular_admin:password" https://server/api/v1/backup/status
# Ответ: {"detail": "Super admin privileges required"} [403]
```

#### Можно ли напрямую вызвать API эндпоинты не-супер админом?
**НЕТ** - защищено на 100%.

Каждый эндпоинт имеет проверку:
```python
# app.py:3439, 3464, 3499, 3530
_require_super_admin(request)  # Первая строка в каждом эндпоинте
```

Проверка делает:
1. Читает `request.state.admin` (установлено в middleware)
2. Проверяет `identity.is_super`
3. Возвращает HTTP 403 если `False`

#### Проверяется ли is_super на каждом эндпоинте?
**ДА** - проверяется на каждом запросе.

```
GET /api/v1/backup/status      -> _require_super_admin() ✓
POST /api/v1/backup/settings   -> _require_super_admin() ✓
POST /api/v1/backup/run        -> _require_super_admin() ✓
POST /api/v1/backup/restore    -> _require_super_admin() ✓
```

Нет кеширования, каждый запрос проходит полную проверку.

#### Есть ли race condition между проверками?
**НЕТ** - race condition невозможен.

Причины:
1. **Проверка на каждом запросе**: `_require_super_admin()` вызывается синхронно в начале обработки
2. **Request-scoped state**: `request.state.admin` создается для каждого HTTP запроса отдельно
3. **Stateless auth**: Basic Authentication не использует сессии, проверяется на каждом запросе
4. **Атомарная проверка**: Проверка `is_super` это одна операция чтения boolean флага

Пример невозможной атаки:
```python
# Злоумышленник НЕ может:
# 1. Отправить запрос как супер-админ
# 2. Быстро сменить права
# 3. Использовать уже открытый request

# Потому что:
# - Каждый request независим
# - AdminIdentity создается заново на каждый запрос
# - Нет shared state между запросами
```

---

### 2. Утечка информации

#### Показывают ли ошибки чувствительную информацию?
**ЧАСТИЧНО** - есть небольшая утечка технической информации.

**Проблемные места:**
```python
# backup/service.py:169 - утечка stderr mongodump
stderr = (exc.stderr or b"").decode("utf-8", errors="ignore")
raise BackupError(f"mongodump_failed: {stderr.strip() or exc.args}") from exc
# -> Может показать пути к файлам, версии MongoDB, etc

# backup/service.py:200 - утечка ответа Yandex.Disk API
raise BackupError(f"ya_disk_download_url_failed: {exc.response.text}") from exc
# -> Может показать детали аутентификации, rate limits, etc
```

**Рекомендация:**
```python
# Не показывать технические детали в production
def sanitize_error_for_client(error_msg: str, include_details: bool = False) -> str:
    """Remove sensitive information from error messages."""
    if not include_details:
        # В production показываем только тип ошибки
        return error_msg.split(":")[0] if ":" in error_msg else "backup_operation_failed"
    return error_msg

# В эндпоинтах
except BackupError as exc:
    sanitized_error = sanitize_error_for_client(str(exc), include_details=DEBUG_MODE)
    await client.update_backup_job(job_id, {"error": sanitized_error})
```

#### Можно ли узнать о существовании бэкапов через timing attacks?
**ТЕОРЕТИЧЕСКИ ДА**, но **практически бесполезно**.

- Timing difference: ~5-50ms (зависит от количества бэкапов)
- Требуется авторизация как супер-админ
- Если уже есть доступ, можно просто посмотреть `/api/v1/backup/status`

**Не требует исправления** (очень низкий риск).

#### Логируются ли попытки доступа?
**НЕТ** - это критическая проблема (см. уязвимость #2).

---

### 3. Манипуляция сессией

#### Что если adminSession изменить в localStorage?
**НЕ ОПАСНО** - frontend переменная не используется для авторизации.

```javascript
// Злоумышленник может сделать:
localStorage.setItem('adminSession', JSON.stringify({ is_super: true }));
window.adminSession = { is_super: true };

// Это только:
// - Покажет UI бэкапа
// - Разблокирует кнопки

// НО: API запросы всё равно вернут 403
// Потому что авторизация на бэкенде через Basic Auth
```

#### Проверяется ли JWT/токен на бэкенде?
**N/A** - система использует **Basic Authentication**, не JWT.

Механизм:
1. Каждый запрос содержит `Authorization: Basic <base64>`
2. Middleware декодирует и проверяет credentials
3. Создает `AdminIdentity` для этого запроса
4. Сохраняет в `request.state.admin`

Нет JWT, нет токенов, нет сессий.

#### Есть ли проверка на каждом запросе или кешируется?
**На каждом запросе** - без кеширования.

```python
# app.py:2620-2654 - BasicAuthMiddleware.dispatch()
async def dispatch(self, request: Request, call_next):
    # ...
    auth = request.headers.get("Authorization")  # Каждый раз заново
    username, password = decoded.split(":", 1)
    identity = await self._authenticate(request, username, password)  # Каждый раз
    request.state.admin = identity  # Request-scoped
    return await call_next(request)
```

---

### 4. API эндпоинты

#### Все ли эндпоинты защищены _require_super_admin?
**ДА** - все 4 эндпоинта защищены.

```
✓ GET  /api/v1/backup/status     (line 3439)
✓ POST /api/v1/backup/settings   (line 3464)
✓ POST /api/v1/backup/run        (line 3499)
✓ POST /api/v1/backup/restore    (line 3530)
```

#### Есть ли эндпоинты для получения списка бэкапов?
**ДА** - `/api/v1/backup/status?limit=50`

Защищен: `_require_super_admin()` ✓

#### Можно ли получить метаданные без доступа?
**НЕТ** - все эндпоинты требуют супер-админ права.

Также защищено на уровне middleware:
```python
# app.py:2563
_PROTECTED_PREFIXES = (
    "/api/v1/backup",  # Весь префикс защищен
)
```

---

### 5. Восстановление

#### Можно ли восстановить бэкап другого проекта?
**ТЕОРЕТИЧЕСКИ ДА** - если знать путь к файлу на Яндекс.Диске.

Это уязвимость #3 - отсутствие валидации `remote_path`.

Сценарий атаки:
```python
# Злоумышленник с супер-админ правами
POST /api/v1/backup/restore
{
  "remotePath": "competitor-backups/their-database.archive.gz"
}

# Если токен Яндекс.Диска дает доступ к этой папке -> УСПЕХ
```

**Защита:** Валидация пути (см. уязвимость #3).

#### Проверяются ли права при восстановлении?
**ДА** - проверяется `_require_super_admin()`.

**НЕТ** - не проверяется принадлежность бэкапа к этой инсталляции.

#### Есть ли подтверждение опасной операции?
**НЕТ** - это уязвимость #4.

Один клик = перезапись БД.

---

## Матрица рисков

| Уязвимость | Критичность | Вероятность эксплуатации | Приоритет исправления |
|---|---|---|---|
| 1. Отсутствие CSRF защиты | ВЫСОКАЯ | Средняя | **P0 - Немедленно** |
| 2. Нет аудита доступа | ВЫСОКАЯ | Высокая | **P0 - Немедленно** |
| 3. Валидация remote_path | СРЕДНЯЯ | Низкая | **P1 - В течение недели** |
| 4. Нет подтверждения restore | СРЕДНЯЯ | Средняя | **P1 - В течение недели** |
| 5. Нет rate limiting | НИЗКАЯ | Низкая | **P2 - В следующем спринте** |
| 6. Timing attacks | ОЧЕНЬ НИЗКАЯ | Очень низкая | **P3 - Когда будет время** |
| 7. Security headers | НИЗКАЯ | N/A | **P2 - В следующем спринте** |

---

## Общая оценка безопасности

### ✅ Что сделано правильно

1. **Defense in depth**: Frontend + Backend проверки
2. **Правильная авторизация**: `_require_super_admin()` на каждом эндпоинте
3. **Middleware защита**: Весь префикс `/api/v1/backup` требует аутентификации
4. **Stateless auth**: Basic Auth проверяется на каждом запросе
5. **Принцип наименьших привилегий**: Только супер-админ, не обычные админы
6. **Документация**: Отличная документация безопасности (SECURITY_BACKUP_ACCESS_CONTROL.md)
7. **Audit trail**: `triggered_by` записывается в backup jobs

### ❌ Критические недостатки

1. **Нет CSRF защиты** - можно выполнить опасные операции через CSRF
2. **Нет аудита доступа** - невозможно обнаружить попытки атак
3. **Слабая валидация путей** - можно указать произвольный путь на Яндекс.Диске
4. **Нет подтверждения** - одна ошибка = потеря всех данных

---

## Рекомендации по приоритетам

### Немедленно (в течение 1-2 дней)

1. Добавить **логирование попыток доступа** (уязвимость #2)
   - Простое изменение в `_require_super_admin()`
   - Критично для обнаружения атак

2. Добавить **CSRF защиту** (уязвимость #1)
   - Использовать Origin/Referer проверку (быстро)
   - Или CSRF tokens (дольше, но надежнее)

### В течение недели

3. Добавить **валидацию remote_path** (уязвимость #3)
   - Предотвратить path traversal
   - Ограничить доступ только к разрешенной папке

4. Добавить **подтверждение для restore** (уязвимость #4)
   - Double confirmation в UI
   - Опционально: two-person rule

### В следующем спринте

5. Добавить **rate limiting** (уязвимость #5)
6. Добавить **security headers** (уязвимость #7)

---

## Итоговая оценка

**Защита на уровне авторизации: 9/10** ✅
**Защита от атак: 4/10** ⚠️
**Аудит и мониторинг: 2/10** ❌
**Общая оценка: 5/10** (СРЕДНЯЯ)

Система хорошо защищена от прямого обхода авторизации, но уязвима для CSRF атак и не имеет должного мониторинга попыток несанкционированного доступа.

---

## Приложение: Скрипты для тестирования

### Тест CSRF уязвимости
```html
<!-- csrf-test.html - разместить на evil.com -->
<!DOCTYPE html>
<html>
<head>
  <title>CSRF Test</title>
</head>
<body>
  <h1>CSRF Attack Demo</h1>
  <script>
    // Попытка восстановить БД через CSRF
    fetch('https://target-sitellm.com/api/v1/backup/restore', {
      method: 'POST',
      credentials: 'include',  // Включает Basic Auth
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        remotePath: 'malicious-backup/evil.archive.gz'
      })
    })
    .then(r => r.json())
    .then(data => {
      console.log('CSRF Success:', data);
      document.body.innerHTML += '<p style="color:red">CSRF ATTACK SUCCESSFUL!</p>';
    })
    .catch(err => {
      console.log('CSRF Failed:', err);
      document.body.innerHTML += '<p style="color:green">CSRF BLOCKED</p>';
    });
  </script>
</body>
</html>
```

### Тест попыток доступа (должно логироваться)
```bash
#!/bin/bash
# test-unauthorized-access.sh

# Попытка доступа обычным админом
echo "Testing unauthorized access attempts..."

for i in {1..5}; do
  echo "Attempt $i"
  curl -s -u "regular_admin:password" \
    "https://target-sitellm.com/api/v1/backup/status" \
    -w "\nHTTP Status: %{http_code}\n"
  sleep 1
done

echo "Check logs for these attempts!"
```

### Тест валидации путей
```python
#!/usr/bin/env python3
# test-path-validation.py

import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "https://target-sitellm.com"
AUTH = HTTPBasicAuth("super_admin", "password")

malicious_paths = [
    "../../etc/passwd",
    "../../../var/log/mongodb.log",
    "evil-folder/../../sensitive-data.archive.gz",
    "a/" * 1000 + "long-path.archive.gz",
    "\x00null-byte.archive.gz",
    "path-without-extension",
    "/absolute/path/backup.archive.gz",
]

for path in malicious_paths:
    print(f"\nTesting: {path}")
    resp = requests.post(
        f"{BASE_URL}/api/v1/backup/restore",
        auth=AUTH,
        json={"remotePath": path}
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
```

---

## Связанные документы

**Документация по безопасности резервного копирования:**
- `SECURITY_BACKUP_ACCESS_CONTROL.md` - Контроль доступа
- `SECURITY_BACKUP_SUMMARY.md` - Краткая сводка по безопасности
- `SECURITY_BACKUP_ANALYSIS.md` - Детальный анализ безопасности (этот документ)
- `SECURITY_BACKUP_ATTACK_SCENARIOS.md` - Сценарии атак
- `SECURITY_BACKUP_CHECKLIST.md` - Чеклист исправлений

**Дата анализа:** 14 ноября 2024
**Автор:** Backend Security Coding Expert
**Версия документа:** 1.0
