# Q&A Import - Быстрые исправления критичных проблем

**Дата создания:** 14 ноября 2024
**Последнее обновление:** 14 ноября 2024
**Версия:** 1.0
**Статус:** Готов к применению

---

## Содержание

1. [Приоритет P0 - Критичные (исправить немедленно)](#приоритет-p0---критичные-исправить-немедленно)
   - [Ограничение размера файла (Backend)](#1-ограничение-размера-файла-backend)
   - [Таймаут для загрузки (Backend)](#2-таймаут-для-загрузки-backend)
   - [Блокировка кнопки (Frontend)](#3-блокировка-кнопки-frontend)
2. [Приоритет P1 - Важные (исправить скоро)](#приоритет-p1---важные-исправить-скоро)
   - [Ограничение длины текста (Backend)](#4-ограничение-длины-текста-backend)
   - [Детектор CSV разделителей (Backend)](#5-детектор-csv-разделителей-backend)
   - [Обработка поврежденного Excel (Backend)](#6-обработка-поврежденного-excel-backend)
3. [Приоритет P2 - Желательные](#приоритет-p2---желательные)
4. [Быстрый чеклист](#быстрый-чеклист)
5. [Как применить](#как-применить)
6. [Тестирование](#тестирование)
7. [Дополнительно](#дополнительно)

---

## Приоритет P0 - Критичные (исправить немедленно)

### 1. Ограничение размера файла (Backend)
**Файл:** `app.py`, строка 3149
**Проблема:** Нет проверки размера файла, может упасть сервер

```python
# ДОБАВИТЬ В НАЧАЛО _read_qa_upload
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Проверка размера файла
file.file.seek(0, 2)
file_size = file.file.tell()
file.file.seek(0)

if file_size > MAX_FILE_SIZE:
    raise HTTPException(
        status_code=400,
        detail=f"Файл слишком большой ({file_size // (1024*1024)} MB). Максимум: 100 MB"
    )

if file_size == 0:
    raise HTTPException(status_code=400, detail="Файл пустой")
```

---

### 2. Таймаут для загрузки (Backend)
**Файл:** `app.py`, строка 3149
**Проблема:** Может зависнуть при загрузке большого файла

```python
import asyncio

# ЗАМЕНИТЬ
payload = await file.read()

# НА
try:
    payload = await asyncio.wait_for(file.read(), timeout=30.0)
except asyncio.TimeoutError:
    raise HTTPException(
        status_code=408,
        detail="Превышено время ожидания загрузки (30 сек)"
    )
```

---

### 3. Блокировка кнопки (Frontend)
**Файл:** `admin/js/index.js`, строки 1905-1962
**Проблема:** Можно нажать несколько раз, множественные загрузки

```javascript
kbQaImportForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    // ... валидация

    const submitBtn = kbQaImportForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;

    // ЗАБЛОКИРОВАТЬ КНОПКУ
    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading…';

    try {
        // ... загрузка
    } finally {
        // РАЗБЛОКИРОВАТЬ
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
});
```

---

## Приоритет P1 - Важные (исправить скоро)

### 4. Ограничение длины текста (Backend)
**Файл:** `app.py`, строки 4296-4298
**Проблема:** Очень длинные вопросы/ответы могут сломать БД

```python
MAX_QUESTION_LENGTH = 1000
MAX_ANSWER_LENGTH = 10000

for pair in pairs:
    question = str(pair.get("question") or "").strip()
    answer = str(pair.get("answer") or "").strip()

    # ДОБАВИТЬ ОБРЕЗКУ
    if len(question) > MAX_QUESTION_LENGTH:
        question = question[:MAX_QUESTION_LENGTH]
    if len(answer) > MAX_ANSWER_LENGTH:
        answer = answer[:MAX_ANSWER_LENGTH]

    if not question or not answer:
        skipped += 1
        continue
```

---

### 5. Детектор CSV разделителей (Backend)
**Файл:** `app.py`, строка 3159
**Проблема:** CSV с `;` или `\t` не читается

```python
import csv

def detect_csv_delimiter(text: str) -> str:
    sample = '\n'.join(text.split('\n')[:5])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
        return dialect.delimiter
    except:
        return ','

# ЗАМЕНИТЬ
reader = csv.reader(io.StringIO(text))

# НА
delimiter = detect_csv_delimiter(text)
reader = csv.reader(io.StringIO(text), delimiter=delimiter)
```

---

### 6. Обработка поврежденного Excel (Backend)
**Файл:** `app.py`, строка 3163
**Проблема:** Неинформативная ошибка "Failed to read QA file"

```python
import zipfile
import openpyxl

# ЗАМЕНИТЬ
wb = load_workbook(filename=io.BytesIO(payload), read_only=True, data_only=True)

# НА
try:
    wb = load_workbook(filename=io.BytesIO(payload), read_only=True, data_only=True)
except openpyxl.utils.exceptions.InvalidFileException:
    raise HTTPException(status_code=400, detail="Файл поврежден или не является Excel")
except zipfile.BadZipFile:
    raise HTTPException(status_code=400, detail="Файл поврежден (ZIP)")
except Exception as exc:
    raise HTTPException(status_code=400, detail=f"Не удалось прочитать Excel: {type(exc).__name__}")
```

---

### 7. Проверка размера файла (Frontend)
**Файл:** `admin/js/index.js`, после строки 1916
**Проблема:** Нет проверки на клиенте, пользователь не видит ошибку сразу

```javascript
// ДОБАВИТЬ ПОСЛЕ const [file] = kbQaFileInput.files;

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100 MB

if (file.size === 0) {
    if (kbQaStatus) kbQaStatus.textContent = 'File is empty (0 bytes)';
    return;
}

if (file.size > MAX_FILE_SIZE) {
    const sizeMB = Math.round(file.size / (1024 * 1024));
    if (kbQaStatus) {
        kbQaStatus.textContent = `File too large (${sizeMB} MB). Maximum: 100 MB`;
    }
    showToast(`File too large: ${sizeMB} MB`, 'error');
    return;
}
```

---

## Приоритет P2 - Желательные

### 8. Индикатор прогресса (Frontend)
**Файл:** `admin/index.html`, после строки 193

```html
<!-- ДОБАВИТЬ -->
<div id="kbQaProgress" class="upload-progress" style="display: none;">
    <div class="progress-bar">
        <div class="progress-fill" id="kbQaProgressFill"></div>
    </div>
    <span class="progress-text" id="kbQaProgressText">0%</span>
</div>
```

**CSS** (добавить в `admin/css/knowledge-panels.css`):
```css
.upload-progress {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 8px;
}

.progress-bar {
    width: 100%;
    height: 8px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #60a5fa, #7c3aed);
    transition: width 0.3s ease;
}

.progress-text {
    font-size: 12px;
    color: var(--color-muted);
    text-align: center;
}
```

**JavaScript** (в обработчике формы):
```javascript
// После formData.set('file', file, file.name || 'qa-upload');

// Показать прогресс
const progressBar = document.getElementById('kbQaProgress');
const progressFill = document.getElementById('kbQaProgressFill');
const progressText = document.getElementById('kbQaProgressText');

if (progressBar) progressBar.style.display = 'flex';

// Использовать XMLHttpRequest для прогресса
const xhr = new XMLHttpRequest();

xhr.upload.addEventListener('progress', (e) => {
    if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        if (progressFill) progressFill.style.width = `${percent}%`;
        if (progressText) progressText.textContent = `${percent}%`;
    }
});

// ... остальной код xhr
```

---

### 9. Дедупликация в файле (Backend)
**Файл:** `app.py`, после строки 4314

```python
# ДОБАВИТЬ ПОСЛЕ normalized.append(...)

# Дедупликация внутри файла
seen_questions = {}
deduplicated = []
duplicates = 0

for pair in normalized:
    q_lower = pair['question'].lower()
    if q_lower in seen_questions:
        duplicates += 1
        continue
    seen_questions[q_lower] = True
    deduplicated.append(pair)

normalized = deduplicated

if duplicates > 0:
    logger.warning("duplicates_removed", count=duplicates)
```

---

### 10. Ограничение количества строк (Backend)
**Файл:** `app.py`, в цикле парсинга

```python
MAX_QA_PAIRS = 10000

# В цикле for row in data_rows:
    # ... обработка
    pairs.append({...})

    # ДОБАВИТЬ
    if len(pairs) >= MAX_QA_PAIRS:
        logger.warning("max_pairs_reached", limit=MAX_QA_PAIRS)
        break
```

---

## Быстрый чеклист

- [ ] **Backend P0:** Ограничение размера файла
- [ ] **Backend P0:** Таймаут загрузки
- [ ] **Frontend P0:** Блокировка кнопки
- [ ] **Backend P1:** Ограничение длины текста
- [ ] **Backend P1:** Детектор CSV разделителей
- [ ] **Backend P1:** Обработка поврежденного Excel
- [ ] **Frontend P1:** Проверка размера файла
- [ ] **Frontend P2:** Индикатор прогресса
- [ ] **Backend P2:** Дедупликация в файле
- [ ] **Backend P2:** Ограничение количества строк

---

## Как применить

### Вариант 1: Минимальные изменения (30 минут)
Применить только P0 исправления:
1. Ограничение размера файла (backend + frontend)
2. Таймаут загрузки (backend)
3. Блокировка кнопки (frontend)

### Вариант 2: Полные исправления (2 часа)
Использовать готовые файлы:
1. Скопировать код из `QA_IMPORT_FIXES.py` в `app.py`
2. Скопировать код из `QA_IMPORT_FIXES.js` в `admin/js/index.js`
3. Добавить HTML/CSS из `QA_IMPORT_FIXES.js`

### Вариант 3: Постепенное внедрение (1 неделя)
- День 1-2: P0 исправления
- День 3-4: P1 исправления
- День 5-7: P2 улучшения + тестирование

---

## Тестирование

После применения исправлений протестировать:

1. **Пустой файл** (0 байт)
2. **Очень большой файл** (> 100 MB)
3. **CSV с разделителем `;`**
4. **Поврежденный Excel**
5. **Файл с дублями**
6. **Файл с очень длинными текстами**
7. **Множественное нажатие на Import**
8. **Отмена во время загрузки** (если реализовано)

---

## Дополнительно

Полный анализ всех 16 краевых случаев в файле:
`QA_IMPORT_EDGE_CASES_ANALYSIS.md`

Готовый код для интеграции:
- `QA_IMPORT_FIXES.py` - backend
- `QA_IMPORT_FIXES.js` - frontend

---

## Связанные документы

**Документация по Q&A импорту:**
- `QA_IMPORT_EDGE_CASES_ANALYSIS.md` - Анализ краевых случаев
- `QA_IMPORT_QUICK_FIXES.md` - Быстрые исправления критичных проблем (этот документ)

**Дата анализа:** 14 ноября 2024
**Автор:** Backend Development Expert
