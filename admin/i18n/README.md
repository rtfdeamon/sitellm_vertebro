# Internationalization (i18n) System

Эта директория содержит систему интернационализации для админ-панели.

## Текущие языки

Система поддерживает **10 языков**:

- **en** (English) - английский язык (по умолчанию)
- **es** (Español) - испанский язык
- **de** (Deutsch) - немецкий язык
- **fr** (Français) - французский язык
- **it** (Italiano) - итальянский язык
- **pt** (Português) - португальский язык
- **ru** (Русский) - русский язык
- **zh** (中文) - китайский язык
- **ja** (日本語) - японский язык
- **ar** (العربية) - арабский язык (RTL)

## Структура файлов

```
i18n/
├── README.md     # Документация (этот файл)
├── i18n.js       # Модуль загрузки и управления переводами
├── en.json       # Английский (базовый)
├── es.json       # Испанский
├── de.json       # Немецкий
├── fr.json       # Французский
├── it.json       # Итальянский
├── pt.json       # Португальский
├── ru.json       # Русский
├── zh.json       # Китайский
├── ja.json       # Японский
└── ar.json       # Арабский (RTL)
```

## Формат файлов переводов

Каждый JSON файл должен содержать следующую структуру:

```json
{
  "name": "Language Name",
  "dir": "ltr",
  "strings": {
    "key1": "Translation 1",
    "key2": "Translation 2",
    ...
  }
}
```

### Поля:

- **name** - отображаемое название языка (например, "English", "Русский")
- **dir** - направление текста: `"ltr"` (слева направо) или `"rtl"` (справа налево)
- **strings** - объект с парами ключ-значение для переводов

### Параметры в переводах

Некоторые строки могут содержать параметры для подстановки:

```json
{
  "crawlerQueued": "В очереди: {value}",
  "authHint": "Учетные данные будут отправлены на {host}."
}
```

Параметры заключаются в фигурные скобки и заменяются при вызове функции `t()`:

```javascript
t('crawlerQueued', { value: '42' })  // → "В очереди: 42"
```

## Добавление нового языка

### Шаг 1: Создайте файл перевода

Создайте новый JSON файл в этой директории с кодом языка в качестве имени (например, `es.json` для испанского):

```json
{
  "name": "Español",
  "dir": "ltr",
  "strings": {
    "headerTitle": "Panel de Control del Rastreador",
    "languageLabel": "Idioma",
    ...
  }
}
```

**Рекомендуется**: Скопируйте `en.json` как шаблон и переведите все значения.

### Шаг 2: Добавьте код языка в index.html

Откройте `/admin/index.html` и найдите массив `SUPPORTED_LANGUAGES`:

```javascript
const SUPPORTED_LANGUAGES = ['en', 'ru'];
```

Добавьте ваш язык:

```javascript
const SUPPORTED_LANGUAGES = ['en', 'ru', 'es'];
```

### Шаг 3: Перезагрузите страницу

После перезагрузки новый язык появится в селекторе языков в правом верхнем углу.

## Список ключей переводов

Всего в системе **159 ключей**. Основные категории:

### Общие элементы интерфейса
- `headerTitle`, `headerSubtitle` - заголовок и подзаголовок
- `buttonLogout`, `buttonReorder`, `buttonReorderDone` - кнопки управления
- `languageLabel` - метка для переключателя языков

### Краулер
- `crawlerStatusTitle`, `crawlerQueued`, `crawlerInProgress`, `crawlerDone`, `crawlerFailed`
- `crawlerStartButton`, `crawlerStopButton`, `crawlerResetButton`
- `crawlerStartUrl`, `crawlerDepth`, `crawlerPages`

### Сервисы и ресурсы
- `servicesTitle`, `resourcesTitle`
- `serviceMongo`, `serviceRedis`, `serviceQdrant`
- `resourceCpuApp`, `resourceRam`, `resourceGpu`

### Авторизация
- `authTitle`, `authPrompt`, `authHint`
- `authUsernameLabel`, `authPasswordLabel`
- `authSubmit`, `authCancel`
- `authErrorMissing`, `authErrorInvalid`, `authErrorNetwork`

### Резервные копии
- `backupCardTitle`, `backupScheduleTitle`, `backupManualTitle`
- `backupEnableLabel`, `backupTimeLabel`, `backupFolderLabel`
- `backupRunNow`, `backupRestoreButton`

### Обратная связь
- `feedbackSectionTitle`, `feedbackNoItems`
- `feedbackStatusOpen`, `feedbackStatusInProgress`, `feedbackStatusDone`, `feedbackStatusDismissed`

### Голосовое обучение
- `voiceTrainingTitle`, `voiceUploadButton`, `voiceRecordButton`, `voiceTrainButton`

И другие... (см. `en.json` для полного списка)

## Использование в HTML

В HTML-коде используются следующие атрибуты для переводов:

### `data-i18n` - перевод текстового содержимого

```html
<button data-i18n="buttonLogout">Выйти</button>
```

### `data-i18n-placeholder` - перевод placeholder

```html
<input data-i18n-placeholder="authUsernamePlaceholder" />
```

### `data-i18n-aria-label` - перевод aria-label

```html
<select data-i18n-aria-label="languageLabel"></select>
```

### `data-i18n-wrapper` - перевод с параметрами

```html
<div data-i18n-wrapper="crawlerQueued">
  Queued: <span data-i18n-value>0</span>
</div>
```

## API модуля i18n

### `i18n.init(languages)`
Инициализирует i18n и загружает файлы переводов.

```javascript
await i18n.init(['en', 'ru']);
```

### `i18n.t(key, params)`
Возвращает перевод для ключа с подстановкой параметров.

```javascript
i18n.t('crawlerQueued', { value: '42' })
```

### `i18n.setLanguage(lang)`
Устанавливает текущий язык.

```javascript
i18n.setLanguage('ru');
```

### `i18n.getLanguage()`
Возвращает код текущего языка.

```javascript
const currentLang = i18n.getLanguage(); // 'en' или 'ru'
```

### `i18n.getLanguages()`
Возвращает все загруженные языки.

```javascript
const languages = i18n.getLanguages();
// { en: {...}, ru: {...} }
```

### `i18n.getLanguageMetadata(lang)`
Возвращает метаданные языка (name, dir).

```javascript
const meta = i18n.getLanguageMetadata('ru');
// { name: 'Русский', dir: 'ltr' }
```

## Хранение выбранного языка

Выбранный язык автоматически сохраняется в `localStorage` под ключом `admin_language` и восстанавливается при следующем визите.

## Расширяемость

Система спроектирована так, чтобы добавление новых языков было максимально простым:

1. ✅ Один файл на язык (не нужно редактировать HTML)
2. ✅ Автоматическая загрузка переводов
3. ✅ Fallback на английский при отсутствии перевода
4. ✅ Поддержка RTL языков (арабский, иврит)
5. ✅ Параметризованные строки

---

**Разработано**: 27 октября 2025
**Версия**: 1.0
