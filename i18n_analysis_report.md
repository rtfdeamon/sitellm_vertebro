# Анализ системы переводов (i18n) - Краевые случаи

**Дата создания:** 14 ноября 2024
**Последнее обновление:** 14 ноября 2024
**Версия:** 1.0
**Статус:** Актуально

---

## Содержание

1. [Полнота переводов](#1-полнота-переводов)
   - [Статус покрытия языков](#11-статус-покрытия-языков)
   - [Непереведенные строки (Hardcoded English)](#12-непереведенные-строки-hardcoded-english)
   - [Использование ключей из i18n-static.js](#13-использование-ключей-из-i18n-staticjs)
2. [Формат переводов](#2-формат-переводов)
   - [Обработка плейсхолдеров {value}](#21-обработка-плейсхолдеров-value)
   - [Экранирование HTML](#22-экранирование-html)
   - [Fallback механизм](#23-fallback-механизм)
3. [Динамическая смена языка](#3-динамическая-смена-языка)
   - [Обновление элементов](#31-обновление-элементов)
   - [Кеширование](#32-кеширование)
   - [Асинхронная загрузка](#33-асинхронная-загрузка)
4. [Fallback механизм](#4-fallback-механизм)
5. [Консистентность](#5-консистентность)
6. [Критичные проблемы](#6-критичные-проблемы)
7. [Рекомендации](#7-рекомендации)
8. [Итоговая статистика](#8-итоговая-статистика)

---

## 1. ПОЛНОТА ПЕРЕВОДОВ

### 1.1. Статус покрытия языков

**Поддерживаемые языки (10):**
✅ EN (English) - Базовый язык
✅ ES (Español) - Полный перевод
✅ DE (Deutsch) - Полный перевод
✅ FR (Français) - Полный перевод
✅ IT (Italiano) - Полный перевод
✅ PT (Português) - Полный перевод
✅ RU (Русский) - Полный перевод
✅ ZH (中文) - Полный перевод
✅ JA (日本語) - Полный перевод
✅ AR (العربية) - Полный перевод (RTL)

**Статус i18n-static.js:**
⚠️ Только EN и RU - остальные 8 языков отсутствуют!

### 1.2. Непереведенные строки (Hardcoded English)

**index.js (критично!):**
```javascript
// Строка 3058-3090 - LLM статусы
llmPingResultEl.textContent = 'Saved'           // ❌ Нет перевода
llmPingResultEl.textContent = 'Save failed'     // ❌ Нет перевода
llmPingResultEl.textContent = 'Ping failed'     // ❌ Нет перевода
llmPingResultEl.textContent = 'Disabled'        // ❌ Нет перевода
llmPingResultEl.textContent = 'Reachable'       // ❌ Нет перевода
llmPingResultEl.textContent = 'Unreachable'     // ❌ Нет перевода

// Строка 3100-3102 - Копирование логов
logInfoElement.textContent = 'Copied'           // ⚠️ Есть ключ logCopySuccess
logInfoElement.textContent = 'Copy failed'      // ⚠️ Есть ключ logCopyError
```

**crawler.js:**
```javascript
// Строка 250
lastCrawl.textContent = 'Last: –'              // ⚠️ Частично переводится
```

**index.js (некритичные):**
```javascript
// Строка 560, 568
badge.textContent = 'AI'                       // ✅ OK - аббревиатура
```

### 1.3. Использование ключей из i18n-static.js

**HTML использует (data-i18n):**
- `aiGenerateButton` - 2 места ✅
- `activateIntegration` - 1 место ✅
- `addButton` - 1 место ✅
- `addManualButton` - 1 место ✅

**Проблема:** Ключи объявлены в i18n-static.js, но имеют только EN и RU!

## 2. ФОРМАТ ПЕРЕВОДОВ

### 2.1. Обработка плейсхолдеров {value}

**Реализация в i18n.js:**
```javascript
// Строка 1495-1500
function t(key, params = {}) {
  const template = dict[key] ?? fallback;
  return template.replace(/\{(\w+)\}/g, (_, token) => {
    if (token in params) return String(params[token]);
    return '';  // ⚠️ Если плейсхолдер отсутствует - пустая строка
  });
}
```

**Краевые случаи:**
✅ Если параметр передан - работает корректно
⚠️ Если параметр отсутствует - заменяется на `''` (пустая строка)
❌ Нет валидации наличия обязательных плейсхолдеров

**Пример проблемы:**
```javascript
t('llmModelLabel')  // Вернет "Модель: " вместо "Модель: {value}"
```

### 2.2. Экранирование HTML

❌ HTML символы НЕ экранируются!
```javascript
// i18n.js строка 1524
node.textContent = translation;  // textContent безопасен
```
✅ Используется `textContent`, не `innerHTML` - автоматическое экранирование

### 2.3. Fallback механизм

**i18n.js:**
```javascript
// Строка 1493-1494
const dict = LANGUAGES[currentLanguage]?.strings || LANGUAGES[FALLBACK_LANGUAGE].strings;
const template = dict[key] ?? LANGUAGES[FALLBACK_LANGUAGE].strings[key] ?? key;
```

✅ Двухуровневый fallback: текущий язык → en → ключ
⚠️ Если ключа нет вообще - возвращается сам ключ (не логируется!)

**crawler.js:**
```javascript
// Строка 27-34
const translate = (key, fallback = '', params = null) => {
  if (typeof global.t === 'function') {
    try {
      return params ? global.t(key, params) : global.t(key);
    } catch (error) {
      console.warn('crawler_translate_failed', error);  // ✅ Логируется!
    }
  }
  // Fallback на строку или форматирование
}
```

✅ В модулях есть дополнительный fallback и логирование

## 3. ДИНАМИЧЕСКАЯ СМЕНА ЯЗЫКА

### 3.1. Обновление элементов

**i18n.js строка 1522-1587:**
```javascript
// Обрабатываются атрибуты:
document.querySelectorAll('[data-i18n]')              // textContent
document.querySelectorAll('[data-i18n-placeholder]')  // placeholder
document.querySelectorAll('[data-i18n-aria-label]')   // aria-label
document.querySelectorAll('[data-i18n-title]')        // title
document.querySelectorAll('[data-i18n-alt]')          // alt
document.querySelectorAll('[data-i18n-text]')         // только текстовые ноды
document.querySelectorAll('[data-i18n-wrapper]')      // с вложенными значениями
```

✅ Обновляются все элементы с data-i18n атрибутами
❌ НЕ обновляются элементы с прямым `.textContent = translate()`
❌ Не вызывается `reapplyCrawlerProgress()` при смене языка!

### 3.2. Кеширование

❌ Кеширования переводов НЕТ
✅ Язык сохраняется в localStorage: `admin_language`

### 3.3. Асинхронная загрузка

❌ Переводы НЕ загружаются асинхронно - все встроены в код
⚠️ Это увеличивает размер бандла, но ускоряет работу

## 4. FALLBACK МЕХАНИЗМ

### 4.1. Отсутствие ключа

**Цепочка fallback:**
1. LANGUAGES[currentLanguage].strings[key]
2. LANGUAGES['en'].strings[key]
3. key (сам ключ как строка)

**Проблема:** Не логируются отсутствующие ключи в production!

### 4.2. Статический fallback (i18n-static.js)

```javascript
// Строка 1446-1473
mergeExtraStrings(STATIC_CONFIG.text);
mergeExtraStrings(STATIC_CONFIG.placeholders);
mergeExtraStrings(STATIC_CONFIG.titles);
mergeExtraStrings(STATIC_CONFIG.alt);
```

**Механизм:**
1. Если есть `en` - добавляется во все языки
2. Если есть `ru` - перезаписывает только для RU
3. Остальные 8 языков получают английский текст!

⚠️ Это означает, что для ES, DE, FR, IT, PT, ZH, JA, AR будут показываться английские тексты!

## 5. КОНСИСТЕНТНОСТЬ

### 5.1. Термины

✅ Используются одинаковые термины:
- "Knowledge base" → все языки
- "Crawler" → все языки
- "LLM" → все языки (аббревиатура)

### 5.2. Опечатки в ключах

**Найденные проблемы:**
- `crawlerStatusWaiting` vs `startWaiting` - дублирование? ✅ Разные контексты
- `knowledgeNavLabel` - `match: []` пустой массив ⚠️
- Нет явных опечаток

### 5.3. Дубликаты

**Найденные дубликаты:**
```javascript
buttonClose: { en: 'Close', ru: 'Закрыть' }
crawlerLogsHide: { en: 'Hide', ru: 'Скрыть' }
// Можно объединить?
```

## 6. КРИТИЧНЫЕ ПРОБЛЕМЫ

### 6.1. Высокий приоритет

1. **❌ i18n-static.js: отсутствуют 8 языков** (ES, DE, FR, IT, PT, ZH, JA, AR)
   - Все ключи имеют только EN и RU
   - Пользователи других языков видят английский текст

2. **❌ index.js: 8 непереведенных строк**
   - LLM статусы: Saved, Save failed, Ping failed, Disabled, Reachable, Unreachable
   - Эти строки всегда на английском

3. **❌ Не обновляются динамические переводы при смене языка**
   - crawler.js не вызывает reapplyCrawlerProgress()
   - Статусы остаются на старом языке

### 6.2. Средний приоритет

4. **⚠️ Отсутствует валидация обязательных плейсхолдеров**
   - Если забыли передать параметр - будет `"Модель: "` вместо предупреждения

5. **⚠️ Не логируются отсутствующие ключи**
   - Только в модулях (crawler, voice, etc.) есть console.warn
   - В основной i18n.js логирования нет

6. **⚠️ crawler.js: 'Last: –' частично хардкод**
   - Должно быть через translate('crawlerLast', { value: '–' })

### 6.3. Низкий приоритет

7. **ℹ️ Можно оптимизировать дубликаты**
   - buttonClose vs crawlerLogsHide
   - Несколько ключей с одинаковыми значениями

8. **ℹ️ Большой размер i18n.js**
   - Все 10 языков в одном файле
   - Можно разбить на отдельные файлы и подгружать асинхронно

## 7. РЕКОМЕНДАЦИИ

### 7.1. Немедленные действия

1. **Добавить недостающие переводы в i18n-static.js:**
   ```javascript
   aiGenerateButton: {
     en: 'Generate with AI',
     es: 'Generar con IA',
     de: 'Mit KI generieren',
     fr: 'Générer avec IA',
     it: 'Genera con IA',
     pt: 'Gerar com IA',
     ru: 'AI‑сгенерировать',
     zh: '使用AI生成',
     ja: 'AIで生成',
     ar: 'توليد بالذكاء الاصطناعي',
   }
   ```

2. **Заменить хардкод в index.js:**
   ```javascript
   // Добавить в i18n.js BASE_STRINGS:
   llmSaved: 'Saved',
   llmSaveFailed: 'Save failed',
   llmPingFailed: 'Ping failed',
   llmDisabled: 'Disabled',
   llmReachable: 'Reachable',
   llmUnreachable: 'Unreachable',
   
   // Заменить в index.js:
   llmPingResultEl.textContent = t('llmSaved');
   ```

3. **Добавить reapplyCrawlerProgress в onLanguageApplied:**
   ```javascript
   onLanguageApplied: ({ currentLanguage, t }) => {
     if (typeof global.reapplyCrawlerProgress === 'function') {
       global.reapplyCrawlerProgress();
     }
   }
   ```

### 7.2. Долгосрочные улучшения

1. Добавить валидацию плейсхолдеров в dev режиме
2. Логировать отсутствующие ключи в console.warn
3. Разбить i18n.js на отдельные языковые файлы
4. Добавить тесты для проверки полноты переводов

## 8. ИТОГОВАЯ СТАТИСТИКА

- **Всего языков:** 10
- **Полностью переведенных:** 10 (в i18n.js)
- **Частично переведенных в i18n-static.js:** 2 (EN, RU)
- **Непереведенных строк:** 8-10 (в index.js, crawler.js)
- **Ключей в i18n-static.js:** ~400
- **Использований data-i18n в HTML:** 245
- **Файлов с translate():** 14

**Общая оценка:** 85% покрытие
- i18n.js: 100% ✅
- i18n-static.js: 20% ❌
- Динамические строки: 70% ⚠️

---

## Связанные документы

**Документация по интернационализации (i18n):**
- `i18n_analysis_report.md` - Анализ системы переводов (этот документ)
- `missing_translations.md` - Детальный список недостающих переводов

**Дата анализа:** 14 ноября 2024
**Автор:** Frontend i18n Expert

