# Анализ краевых случаев (Edge Cases) Q&A импорта

**Дата создания:** 14 ноября 2024
**Последнее обновление:** 14 ноября 2024
**Версия:** 1.0
**Статус:** Актуально

---

## Содержание

1. [Валидация файлов](#1-валидация-файлов)
   - [Пустой файл (0 байт)](#11-пустой-файл-0-байт--обрабатывается)
   - [Очень большой файл (> 100 MB)](#12-очень-большой-файл--100-mb--не-обрабатывается)
   - [Неправильная кодировка (не UTF-8)](#13-неправильная-кодировка-не-utf-8-️-частично-обрабатывается)
   - [CSV с неправильными разделителями](#14-csv-с-неправильными-разделителями--не-обрабатывается)
   - [Поврежденный Excel файл](#15-поврежденный-excel-файл--не-обрабатывается)
2. [Формат данных](#2-формат-данных)
3. [Обработка ошибок](#3-обработка-ошибок)
4. [UI/UX проблемы](#4-uiux-проблемы)
5. [Дополнительные Edge Cases](#5-дополнительные-edge-cases)
6. [Безопасность](#6-безопасность)
7. [Производительность](#7-производительность)
8. [Сводная таблица проблем](#сводная-таблица-проблем)
9. [Приоритетные исправления](#приоритетные-исправления)
10. [Заключение](#заключение)

---

## 1. ВАЛИДАЦИЯ ФАЙЛОВ

### 1.1 Пустой файл (0 байт) ✅ ОБРАБАТЫВАЕТСЯ
**Файл:** `app.py:3149-3151`
```python
payload = await file.read()
if not payload:
    raise HTTPException(status_code=400, detail="Файл пустой")
```
**Статус:** Обрабатывается корректно

---

### 1.2 Очень большой файл (> 100 MB) ❌ НЕ ОБРАБАТЫВАЕТСЯ
**Проблема:** Отсутствует валидация размера файла
- Нет проверки на максимальный размер
- Файл полностью загружается в память (`await file.read()`)
- Может привести к исчерпанию памяти сервера

**Местоположение:** `app.py:4260-4275`, `app.py:3149`

**Рекомендация:**
```python
# Добавить в начало функции _read_qa_upload
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

async def _read_qa_upload(file: UploadFile) -> list[dict[str, str]]:
    # Проверка размера файла
    file.file.seek(0, 2)  # Переместить курсор в конец
    file_size = file.file.tell()
    file.file.seek(0)  # Вернуть курсор в начало

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // (1024*1024)} MB"
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Файл пустой")

    payload = await file.read()
    # ... остальной код
```

---

### 1.3 Неправильная кодировка (не UTF-8) ⚠️ ЧАСТИЧНО ОБРАБАТЫВАЕТСЯ
**Файл:** `app.py:3155-3158`
```python
if ext == ".csv":
    try:
        text = payload.decode("utf-8-sig", errors="ignore")
    except Exception:
        text = payload.decode("cp1251", errors="ignore")
```

**Проблемы:**
1. Используется `errors="ignore"` - символы могут теряться без уведомления
2. Поддерживается только UTF-8 и CP1251
3. Другие кодировки (ISO-8859-1, Latin-1, KOI8-R) не поддерживаются
4. Пользователь не получает предупреждение о потере данных

**Рекомендация:**
```python
def detect_encoding(payload: bytes) -> str:
    """Определить кодировку файла с помощью chardet"""
    import chardet
    result = chardet.detect(payload)
    return result['encoding'] or 'utf-8'

if ext == ".csv":
    detected_encoding = detect_encoding(payload)
    try:
        text = payload.decode(detected_encoding)
    except UnicodeDecodeError:
        # Fallback с логированием
        logger.warning(
            "csv_encoding_failed",
            detected=detected_encoding,
            fallback="utf-8"
        )
        text = payload.decode("utf-8", errors="replace")
        # Проверить наличие символов замены
        if '\ufffd' in text:
            raise HTTPException(
                status_code=400,
                detail=f"Не удалось корректно прочитать файл. Обнаружена кодировка: {detected_encoding}"
            )
```

---

### 1.4 CSV с неправильными разделителями ❌ НЕ ОБРАБАТЫВАЕТСЯ
**Файл:** `app.py:3159`
```python
reader = csv.reader(io.StringIO(text))
```

**Проблема:**
- Используется только стандартный разделитель (запятая)
- Не поддерживаются: точка с запятой (`;`), табуляция (`\t`), другие разделители
- CSV файлы из Excel часто используют `;` в европейской локали

**Рекомендация:**
```python
def detect_csv_delimiter(text: str) -> str:
    """Определить разделитель CSV"""
    import csv
    sample = '\n'.join(text.split('\n')[:5])  # Первые 5 строк
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters=',;\t|')
        return dialect.delimiter
    except Exception:
        return ','  # По умолчанию запятая

if ext == ".csv":
    text = payload.decode("utf-8-sig", errors="ignore")
    delimiter = detect_csv_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    for raw in reader:
        rows.append([str(cell).strip() for cell in raw])
```

---

### 1.5 Поврежденный Excel файл ❌ НЕ ОБРАБАТЫВАЕТСЯ
**Файл:** `app.py:3163`
```python
wb = load_workbook(filename=io.BytesIO(payload), read_only=True, data_only=True)
```

**Проблема:**
- Если Excel файл поврежден, `load_workbook` выбросит исключение
- Исключение перехватывается общим catch в `app.py:4273`, но сообщение об ошибке неинформативное

**Текущий обработчик:**
```python
except Exception as exc:  # noqa: BLE001
    logger.error("knowledge_qa_import_parse_failed", project=project_name, error=str(exc))
    raise HTTPException(status_code=400, detail="Failed to read QA file") from exc
```

**Рекомендация:**
```python
else:  # Excel файл
    try:
        wb = load_workbook(
            filename=io.BytesIO(payload),
            read_only=True,
            data_only=True
        )
    except openpyxl.utils.exceptions.InvalidFileException:
        raise HTTPException(
            status_code=400,
            detail="Файл поврежден или не является корректным Excel документом"
        )
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="Файл поврежден (неверная структура ZIP)"
        )
    except Exception as exc:
        logger.error("excel_load_failed", error=str(exc))
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось прочитать Excel файл: {type(exc).__name__}"
        )

    sheet = wb.active
    if sheet is None:
        raise HTTPException(
            status_code=400,
            detail="Excel файл не содержит активного листа"
        )
```

---

## 2. ФОРМАТ ДАННЫХ

### 2.1 CSV только с заголовками, без данных ✅ ОБРАБАТЫВАЕТСЯ
**Файл:** `app.py:3168-3180`
```python
if not rows:
    return []
```
**Статус:** Возвращается пустой массив, корректно обрабатывается в `app.py:4277-4281`

---

### 2.2 Колонки названы неправильно ✅ ЧАСТИЧНО ОБРАБАТЫВАЕТСЯ
**Файл:** `app.py:3118-3137` (`_detect_qa_columns`)

**Поддерживаемые варианты:**
- Question: "вопрос", "question", "q:"
- Answer: "ответ", "answer", "a:"
- Priority: "priority", "приоритет", "prio"

**Fallback поведение:**
```python
if question_idx == -1 and len(header) >= 1:
    question_idx = 0
if answer_idx == -1 and len(header) >= 2:
    answer_idx = 1
```

**Проблемы:**
1. Регистронезависимый поиск - ✅ работает
2. Но нет уведомления пользователю, что колонки определены автоматически
3. Нет проверки на некорректные названия колонок (например "Q&A", "FAQ")

**Рекомендация:**
```python
def _detect_qa_columns(header: list[str]) -> tuple[int, int, int, list[str]]:
    """Вернуть индексы и предупреждения"""
    question_idx = -1
    answer_idx = -1
    priority_idx = -1
    warnings = []

    for idx, title in enumerate(header):
        lowered = title.lower()
        if question_idx == -1 and any(token in lowered for token in ("вопрос", "question", "q:")):
            question_idx = idx
        if answer_idx == -1 and any(token in lowered for token in ("ответ", "answer", "a:")):
            answer_idx = idx
        if priority_idx == -1 and any(token in lowered for token in ("priority", "приоритет", "prio")):
            priority_idx = idx

    # Автоматическое определение
    if question_idx == -1 and len(header) >= 1:
        question_idx = 0
        warnings.append(f"Колонка вопросов не найдена, использована первая колонка: '{header[0]}'")
    if answer_idx == -1 and len(header) >= 2:
        answer_idx = 1
        warnings.append(f"Колонка ответов не найдена, использована вторая колонка: '{header[1]}'")

    return question_idx, answer_idx, priority_idx, warnings
```

---

### 2.3 Специальные символы, HTML, SQL инъекции ⚠️ ЧАСТИЧНО ОБРАБАТЫВАЕТСЯ

**Текущая обработка:**
```python
question = str(pair.get("question") or "").strip()
answer = str(pair.get("answer") or "").strip()
```

**Проблемы:**
1. **HTML не экранируется** - если в ответе есть `<script>alert('xss')</script>`, он сохранится как есть
2. **SQL инъекции** - при использовании MongoDB риск минимален (параметризованные запросы), но данные не санитизируются
3. **Специальные символы** - сохраняются как есть (может быть проблемой при отображении)

**Рекомендация:**
```python
import html
import re

def sanitize_text(text: str, max_length: int = 10000) -> str:
    """Очистить и валидировать текст"""
    # Обрезать до максимальной длины
    text = text[:max_length]

    # Удалить NULL байты
    text = text.replace('\x00', '')

    # Экранировать HTML (опционально - зависит от использования)
    # text = html.escape(text)

    # Удалить управляющие символы кроме \n, \r, \t
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)

    return text.strip()

# Применить в нормализации
for pair in pairs:
    question = sanitize_text(str(pair.get("question") or ""))
    answer = sanitize_text(str(pair.get("answer") or ""))
    if not question or not answer:
        skipped += 1
        continue
    # ...
```

---

### 2.4 Пустые строки или только пробелы ✅ ОБРАБАТЫВАЕТСЯ
**Файл:** `app.py:3186-3189`, `app.py:4296-4300`
```python
question = (row[q_idx] or "").strip()
answer = (row[a_idx] or "").strip() if 0 <= a_idx < len(row) else ""
if not question or not answer:
    continue
```
```python
if not question or not answer:
    skipped += 1
    continue
```
**Статус:** Корректно пропускаются

---

### 2.5 Очень длинные вопросы/ответы (> 10000 символов) ❌ НЕ ОБРАБАТЫВАЕТСЯ

**Проблема:**
- Нет ограничения на длину вопроса/ответа
- Может привести к проблемам с базой данных
- Может сломать UI при отображении
- Может превысить контекстное окно LLM

**Рекомендация:**
```python
MAX_QUESTION_LENGTH = 1000  # символов
MAX_ANSWER_LENGTH = 10000   # символов

for pair in pairs:
    question = str(pair.get("question") or "").strip()
    answer = str(pair.get("answer") or "").strip()

    if len(question) > MAX_QUESTION_LENGTH:
        logger.warning(
            "question_too_long",
            length=len(question),
            max=MAX_QUESTION_LENGTH,
            preview=question[:100]
        )
        question = question[:MAX_QUESTION_LENGTH]

    if len(answer) > MAX_ANSWER_LENGTH:
        logger.warning(
            "answer_too_long",
            length=len(answer),
            max=MAX_ANSWER_LENGTH,
            preview=answer[:100]
        )
        answer = answer[:MAX_ANSWER_LENGTH]

    if not question or not answer:
        skipped += 1
        continue
```

---

## 3. ОБРАБОТКА ОШИБОК

### 3.1 Таймаут для загрузки ❌ НЕ ОБРАБАТЫВАЕТСЯ

**Проблема:**
- Нет таймаута для чтения файла
- Нет таймаута для обработки файла
- При большом файле запрос может зависнуть

**Рекомендация:**
```python
import asyncio

async def _read_qa_upload(file: UploadFile) -> list[dict[str, str]]:
    """Parse uploaded Excel/CSV into question-answer pairs."""

    # Таймаут на чтение файла
    try:
        payload = await asyncio.wait_for(file.read(), timeout=30.0)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Превышено время ожидания загрузки файла (30 сек)"
        )

    # ... остальной код
```

**И на уровне endpoint:**
```python
from fastapi import BackgroundTasks

@app.post("/api/v1/admin/knowledge/qa/upload", response_class=ORJSONResponse, status_code=201)
async def admin_import_knowledge_qa_file(
    request: Request,
    project: str = Form(...),
    file: UploadFile = File(...),
    refine: str | None = Form(None),
) -> ORJSONResponse:
    # Установить таймаут для всего запроса
    try:
        result = await asyncio.wait_for(
            _process_qa_upload(request, project, file, refine),
            timeout=300.0  # 5 минут
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Превышено время обработки файла (5 минут)"
        )
```

---

### 3.2 Обрыв соединения ❌ НЕ ОБРАБАТЫВАЕТСЯ

**Проблема:**
- Если клиент отключится во время загрузки, сервер продолжит обработку
- Нет механизма отмены обработки

**Рекомендация:**
```python
from starlette.requests import Request

async def _read_qa_upload(file: UploadFile, request: Request | None = None) -> list[dict[str, str]]:
    """Parse uploaded Excel/CSV into question-answer pairs."""

    # Проверка соединения перед чтением
    if request and await request.is_disconnected():
        raise HTTPException(status_code=499, detail="Клиент отключился")

    payload = await file.read()

    # ... обработка файла

    # Периодическая проверка во время обработки больших файлов
    if request and await request.is_disconnected():
        raise HTTPException(status_code=499, detail="Клиент отключился во время обработки")

    return pairs
```

---

### 3.3 Детальные ошибки пользователю ⚠️ ЧАСТИЧНО ПОКАЗЫВАЮТСЯ

**Текущая обработка:**
```python
# Frontend: admin/js/index.js:1952-1960
catch (error) {
    console.error('knowledge_qa_import_failed', error);
    const message = translateText(
        'knowledgeQaImportError',
        'Failed to import file: {error}',
        { error: getErrorMessage(error) },
    );
    if (kbQaStatus) kbQaStatus.textContent = message;
    showToast(message, 'error');
}
```

**Проблемы:**
1. Сообщения об ошибках на английском, но в коде есть русские
2. Нет детальной информации (например, какая строка файла содержит ошибку)
3. Общее сообщение "Failed to read QA file" не помогает пользователю

**Рекомендация:**
Добавить структурированные ошибки:
```python
class QAImportError(HTTPException):
    def __init__(self, code: str, detail: str, row: int | None = None, **extra):
        super().__init__(status_code=400, detail=detail)
        self.code = code
        self.row = row
        self.extra = extra

# Использование
if not question or not answer:
    raise QAImportError(
        code="empty_fields",
        detail=f"Строка {row_num}: пустой вопрос или ответ",
        row=row_num,
        question=question,
        answer=answer
    )
```

---

### 3.4 Можно ли отменить загрузку? ❌ НЕВОЗМОЖНО

**Frontend:** `admin/js/index.js:1905-1962`

**Проблемы:**
1. Нет кнопки "Отмена" во время загрузки
2. Нет индикатора прогресса
3. Пользователь видит только "Importing…"

**Рекомендация:**
```javascript
// Добавить AbortController
let uploadAbortController = null;

kbQaImportForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    // ... валидация

    // Создать контроллер отмены
    uploadAbortController = new AbortController();

    if (kbQaStatus) kbQaStatus.textContent = translateOr('knowledgeQaImporting', 'Importing…');

    // Показать кнопку отмены
    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancel';
    cancelBtn.onclick = () => {
        uploadAbortController.abort();
        kbQaStatus.textContent = 'Import cancelled';
    };
    kbQaStatus.appendChild(cancelBtn);

    try {
        const formData = new FormData();
        formData.set('project', projectKey);
        formData.set('file', file, file.name || 'qa-upload');

        const resp = await fetchWithAdminAuth('/api/v1/admin/knowledge/qa/upload', {
            method: 'POST',
            body: formData,
            signal: uploadAbortController.signal,  // Добавить сигнал отмены
        });

        // ... остальной код
    } catch (error) {
        if (error.name === 'AbortError') {
            kbQaStatus.textContent = 'Import cancelled by user';
            return;
        }
        // ... обработка других ошибок
    } finally {
        uploadAbortController = null;
        cancelBtn.remove();
    }
});
```

---

## 4. UI/UX ПРОБЛЕМЫ

### 4.1 Блокировка кнопки во время загрузки ❌ НЕ БЛОКИРУЕТСЯ

**Frontend:** `admin/js/index.js:1905-1962`

**Проблема:**
- Кнопка "Import" не блокируется
- Пользователь может нажать несколько раз
- Может привести к множественным загрузкам

**Рекомендация:**
```javascript
kbQaImportForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    // ... валидация

    const submitBtn = kbQaImportForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;

    // Заблокировать кнопку
    submitBtn.disabled = true;
    submitBtn.textContent = 'Importing...';

    try {
        // ... загрузка
    } finally {
        // Разблокировать кнопку
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
});
```

---

### 4.2 Повторная загрузка без перезагрузки ✅ РАБОТАЕТ

**Frontend:** `admin/js/index.js:1951`
```javascript
if (kbQaImportForm) kbQaImportForm.reset();
```

**Статус:** Форма очищается после успешной загрузки

---

### 4.3 Очистка формы после ошибки ❌ НЕ ОЧИЩАЕТСЯ

**Проблема:**
- После ошибки форма не очищается
- Файл остается выбранным
- Пользователь может случайно загрузить тот же файл снова

**Рекомендация:**
```javascript
catch (error) {
    console.error('knowledge_qa_import_failed', error);
    const message = translateText(
        'knowledgeQaImportError',
        'Failed to import file: {error}',
        { error: getErrorMessage(error) },
    );
    if (kbQaStatus) kbQaStatus.textContent = message;
    showToast(message, 'error');

    // Очистить форму только если это ошибка формата файла
    const errorMsg = getErrorMessage(error).toLowerCase();
    if (errorMsg.includes('формат') || errorMsg.includes('поврежден') || errorMsg.includes('пустой')) {
        if (kbQaImportForm) kbQaImportForm.reset();
    }
}
```

---

### 4.4 Индикатор прогресса ❌ ОТСУТСТВУЕТ

**Проблема:**
- Нет визуального индикатора прогресса
- Пользователь не знает, сколько времени займет загрузка
- Только текст "Importing…"

**Рекомендация:**
Добавить HTML для прогресс-бара в `admin/index.html`:
```html
<div class="qa-actions">
    <button type="submit" data-i18n="buttonImport">Import</button>
    <button type="button" id="kbQaAddRow" data-i18n="addManualButton">Add manually</button>
    <span class="muted" id="kbQaStatus"></span>
    <!-- Добавить прогресс-бар -->
    <div id="kbQaProgress" class="upload-progress" style="display: none;">
        <div class="progress-bar">
            <div class="progress-fill" id="kbQaProgressFill"></div>
        </div>
        <span class="progress-text" id="kbQaProgressText">0%</span>
    </div>
</div>
```

JavaScript:
```javascript
// Показать прогресс
const progressBar = document.getElementById('kbQaProgress');
const progressFill = document.getElementById('kbQaProgressFill');
const progressText = document.getElementById('kbQaProgressText');

if (progressBar) progressBar.style.display = 'block';

try {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            if (progressFill) progressFill.style.width = `${percent}%`;
            if (progressText) progressText.textContent = `${percent}%`;
        }
    });

    // ... остальной код загрузки
} finally {
    if (progressBar) progressBar.style.display = 'none';
}
```

---

## 5. ДОПОЛНИТЕЛЬНЫЕ EDGE CASES

### 5.1 Дублирующиеся вопросы в одном файле ❌ НЕ ОБРАБАТЫВАЕТСЯ

**Проблема:**
- Если файл содержит один и тот же вопрос дважды, оба будут импортированы
- Нет дедупликации внутри файла

**Рекомендация:**
```python
# После парсинга, перед сохранением
seen_questions = {}
deduplicated = []
duplicates = 0

for pair in normalized:
    q_lower = pair['question'].lower()
    if q_lower in seen_questions:
        duplicates += 1
        logger.info(
            "duplicate_question_in_file",
            question=pair['question'],
            existing_answer=seen_questions[q_lower],
            new_answer=pair['answer']
        )
        continue
    seen_questions[q_lower] = pair['answer']
    deduplicated.append(pair)

if duplicates > 0:
    logger.warning("duplicates_removed", count=duplicates, total=len(pairs))
```

---

### 5.2 Excel с несколькими листами ⚠️ ИСПОЛЬЗУЕТСЯ ТОЛЬКО АКТИВНЫЙ

**Файл:** `app.py:3164`
```python
sheet = wb.active
```

**Проблема:**
- Если Excel содержит несколько листов, используется только активный
- Пользователь не предупреждается

**Рекомендация:**
```python
wb = load_workbook(filename=io.BytesIO(payload), read_only=True, data_only=True)
sheet = wb.active

# Проверить наличие других листов
if len(wb.sheetnames) > 1:
    logger.warning(
        "multiple_sheets_detected",
        total=len(wb.sheetnames),
        active=sheet.title,
        all_sheets=wb.sheetnames
    )
    # Можно добавить в ответ предупреждение
```

---

### 5.3 CSV с BOM (Byte Order Mark) ✅ ОБРАБАТЫВАЕТСЯ

**Файл:** `app.py:3156`
```python
text = payload.decode("utf-8-sig", errors="ignore")
```

**Статус:** `utf-8-sig` корректно удаляет BOM

---

### 5.4 Числовые значения вместо текста в Excel ✅ ОБРАБАТЫВАЕТСЯ

**Файл:** `app.py:3166`
```python
rows.append(["" if cell is None else str(cell).strip() for cell in row])
```

**Статус:** Все значения конвертируются в строки

---

### 5.5 Формулы в Excel ✅ ОБРАБАТЫВАЕТСЯ

**Файл:** `app.py:3163`
```python
wb = load_workbook(filename=io.BytesIO(payload), read_only=True, data_only=True)
```

**Статус:** `data_only=True` читает вычисленные значения, а не формулы

---

### 5.6 Пустые строки в середине файла ✅ ОБРАБАТЫВАЕТСЯ

**Файл:** `app.py:3188-3189`
```python
if not question or not answer:
    continue
```

**Статус:** Пустые строки пропускаются

---

### 5.7 Слишком много строк (> 10,000) ❌ НЕ ОГРАНИЧЕНО

**Проблема:**
- Нет ограничения на количество строк
- Может привести к длительной обработке
- Может исчерпать память

**Рекомендация:**
```python
MAX_QA_PAIRS = 10000

# После парсинга
if len(pairs) > MAX_QA_PAIRS:
    logger.warning(
        "too_many_pairs",
        total=len(pairs),
        max=MAX_QA_PAIRS,
        truncated=True
    )
    pairs = pairs[:MAX_QA_PAIRS]
    # Можно добавить в ответ предупреждение
```

---

## 6. БЕЗОПАСНОСТЬ

### 6.1 MIME Type Validation ❌ ОТСУТСТВУЕТ

**Проблема:**
- Проверяется только расширение файла
- Можно загрузить `.exe` переименованный в `.xlsx`

**Рекомендация:**
```python
import magic  # python-magic

async def _read_qa_upload(file: UploadFile) -> list[dict[str, str]]:
    filename = file.filename or "qa.xlsx"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in QA_SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Формат файла не поддерживается")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Файл пустой")

    # Проверить MIME type
    mime = magic.from_buffer(payload, mime=True)
    allowed_mimes = {
        'text/csv',
        'text/plain',  # CSV может определяться как text/plain
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
    }

    if mime not in allowed_mimes:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип файла: {mime}. Ожидается CSV или Excel."
        )

    # ... остальной код
```

---

### 6.2 Path Traversal в filename ⚠️ ЧАСТИЧНО ЗАЩИЩЕНО

**Файл:** `app.py:3144`
```python
filename = file.filename or "qa.xlsx"
ext = os.path.splitext(filename)[1].lower()
```

**Анализ:**
- Имя файла используется только для определения расширения
- Файл не сохраняется на диск
- Риск минимален, но лучше санитизировать

**Рекомендация:**
```python
import os

def sanitize_filename(filename: str | None) -> str:
    if not filename:
        return "qa.xlsx"
    # Получить только имя файла без пути
    basename = os.path.basename(filename)
    # Удалить опасные символы
    safe = re.sub(r'[^a-zA-Z0-9._-]', '_', basename)
    return safe or "qa.xlsx"

filename = sanitize_filename(file.filename)
```

---

## 7. ПРОИЗВОДИТЕЛЬНОСТЬ

### 7.1 Обработка больших файлов в памяти ❌ НЕОПТИМАЛЬНО

**Проблема:**
- Весь файл загружается в память
- При большом файле может исчерпаться память
- Нет streaming обработки

**Рекомендация:**
Для CSV можно использовать streaming:
```python
async def _read_csv_streaming(file: UploadFile, max_rows: int = 10000) -> list[dict[str, str]]:
    """Потоковое чтение CSV"""
    import aiofiles

    # Сохранить во временный файл
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    try:
        pairs = []
        async with aiofiles.open(tmp_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(await f.readlines())
            header = next(reader, None)
            if not header:
                return []

            q_idx, a_idx, p_idx = _detect_qa_columns(header)

            for i, row in enumerate(reader):
                if i >= max_rows:
                    logger.warning("max_rows_reached", limit=max_rows)
                    break

                # ... обработка строки

        return pairs
    finally:
        os.unlink(tmp_path)
```

---

## СВОДНАЯ ТАБЛИЦА ПРОБЛЕМ

| # | Проблема | Критичность | Статус | Файл | Строки |
|---|----------|-------------|--------|------|--------|
| 1 | Нет ограничения размера файла | ВЫСОКАЯ | ❌ | app.py | 3149 |
| 2 | Потеря данных при ошибке кодировки | СРЕДНЯЯ | ⚠️ | app.py | 3156 |
| 3 | Не поддерживаются разные разделители CSV | СРЕДНЯЯ | ❌ | app.py | 3159 |
| 4 | Неинформативные ошибки поврежденного Excel | СРЕДНЯЯ | ❌ | app.py | 3163 |
| 5 | Нет ограничения длины текста | СРЕДНЯЯ | ❌ | app.py | 4296-4298 |
| 6 | Нет санитизации HTML/спецсимволов | СРЕДНЯЯ | ⚠️ | app.py | 4296-4298 |
| 7 | Нет таймаута загрузки | ВЫСОКАЯ | ❌ | app.py | 4260-4341 |
| 8 | Нет обработки обрыва соединения | НИЗКАЯ | ❌ | app.py | 4260-4341 |
| 9 | Нет отмены загрузки | НИЗКАЯ | ❌ | admin/js/index.js | 1905-1962 |
| 10 | Кнопка не блокируется | СРЕДНЯЯ | ❌ | admin/js/index.js | 1905-1962 |
| 11 | Нет индикатора прогресса | НИЗКАЯ | ❌ | admin/js/index.js | 1924 |
| 12 | Дублирующиеся вопросы в файле | НИЗКАЯ | ❌ | app.py | 4293-4314 |
| 13 | Несколько листов Excel без предупреждения | НИЗКАЯ | ⚠️ | app.py | 3164 |
| 14 | Нет ограничения количества строк | СРЕДНЯЯ | ❌ | app.py | 3183-3199 |
| 15 | Нет проверки MIME type | СРЕДНЯЯ | ❌ | app.py | 3144-3147 |
| 16 | Неоптимальная обработка больших файлов | СРЕДНЯЯ | ❌ | app.py | 3149 |

---

## ПРИОРИТЕТНЫЕ ИСПРАВЛЕНИЯ

### P0 - Критичные (исправить немедленно):
1. **Ограничение размера файла** - может привести к падению сервера
2. **Таймаут загрузки** - может привести к зависанию
3. **Блокировка кнопки** - предотвращает двойную отправку

### P1 - Важные (исправить в ближайшее время):
4. **Ограничение длины текста** - защита от переполнения БД
5. **Проверка MIME type** - безопасность
6. **Детектор разделителей CSV** - улучшение UX
7. **Обработка ошибок кодировки** - предотвращение потери данных

### P2 - Желательные (можно отложить):
8. **Индикатор прогресса** - улучшение UX
9. **Отмена загрузки** - улучшение UX
10. **Дедупликация внутри файла** - качество данных
11. **Ограничение количества строк** - производительность
12. **Санитизация HTML** - безопасность отображения

---

## ЗАКЛЮЧЕНИЕ

Всего обнаружено **16 краевых случаев**:
- ✅ **6 обрабатываются корректно**
- ⚠️ **4 обрабатываются частично**
- ❌ **6 не обрабатываются вообще**

Наиболее критичные проблемы связаны с:
1. Отсутствием ограничений (размер файла, длина текста, количество строк)
2. Отсутствием таймаутов и защиты от зависания
3. Недостаточной валидацией входных данных
4. Неоптимальной обработкой больших файлов в памяти

Рекомендуется начать с исправления критичных проблем (P0), затем перейти к важным (P1).

---

## Связанные документы

**Документация по Q&A импорту:**
- `QA_IMPORT_EDGE_CASES_ANALYSIS.md` - Анализ краевых случаев (этот документ)
- `QA_IMPORT_QUICK_FIXES.md` - Быстрые исправления критичных проблем

**Дата анализа:** 14 ноября 2024
**Автор:** Backend Development Expert

