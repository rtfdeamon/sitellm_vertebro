# Тесты для админ-панели SiteLLM

**Дата актуальности:** 29 октября 2025 г.

## Описание

Данный каталог содержит набор тестов для админ-панели SiteLLM. Тесты написаны с использованием [Vitest](https://vitest.dev/) и покрывают основную функциональность панели администратора.

## Структура тестов

```
tests/
├── README.md                 # Документация (этот файл)
├── setup.js                  # Настройка тестового окружения
├── utils/
│   └── testHelpers.js       # Вспомогательные функции для тестов
├── unit/                    # Модульные тесты
│   ├── auth.test.js        # Тесты аутентификации
│   ├── i18n.test.js        # Тесты интернационализации
│   └── projects.test.js    # Тесты утилит для работы с проектами
└── integration/             # Интеграционные тесты
    └── api.test.js         # Тесты API-взаимодействий
```

## Установка зависимостей

```bash
cd admin
npm install
```

## Запуск тестов

### Запуск всех тестов
```bash
npm test
```

### Запуск тестов с UI-интерфейсом
```bash
npm run test:ui
```

### Запуск тестов с покрытием кода
```bash
npm run test:coverage
```

### Запуск конкретного файла тестов
```bash
npx vitest tests/unit/auth.test.js
```

### Запуск в режиме наблюдения (watch mode)
```bash
npx vitest --watch
```

## Описание тестов

### Модульные тесты (Unit Tests)

#### `tests/unit/auth.test.js` - Аутентификация
Тесты функций аутентификации:
- `getAuthHeaderForBase()` - получение заголовка авторизации из sessionStorage
- `setAuthHeaderForBase()` - сохранение заголовка авторизации
- `clearAuthHeaderForBase()` - очистка данных авторизации
- `getStoredAdminUser()` - получение данных пользователя из localStorage
- `requiresAdminAuth()` - проверка, требует ли URL авторизации админа

Покрывает:
- Хранение токенов в sessionStorage
- Хранение данных пользователя в localStorage
- Обработку невалидного JSON
- Определение защищенных URL-адресов

#### `tests/unit/i18n.test.js` - Интернационализация
Тесты функций перевода:
- `translateInstant()` - мгновенный перевод по ключу
- Подстановка параметров в строки перевода
- Проверка поддерживаемых языков
- Выбор языка по умолчанию
- Сохранение предпочтений языка в localStorage

Покрывает:
- Поддержку 10 языков: en, es, de, fr, it, pt, ru, zh, ja, ar
- Подстановку параметров в формате `{param}`
- Fallback на ключ при отсутствии перевода
- Хранение выбранного языка

#### `tests/unit/projects.test.js` - Утилиты для проектов
Тесты утилит для работы с проектами:
- `normalizeProjectName()` - нормализация названий проектов (trim, lowercase)
- `buildTargetUrl()` - построение целевого URL с автоматическим добавлением https://

Покрывает:
- Обработку пробелов и регистра
- Обработку невалидных входных данных
- Автоматическое добавление протокола HTTPS

### Интеграционные тесты (Integration Tests)

#### `tests/integration/api.test.js` - API-взаимодействия
Тесты взаимодействия с API:
- **Admin Session API**
  - Получение сессии с заголовком авторизации
  - Обработка 401 Unauthorized ответа
- **Admin Logout**
  - Вызов эндпоинта logout
  - Очистка localStorage и sessionStorage
- **Knowledge API**
  - Получение приоритета источников знаний
  - Сохранение приоритета источников знаний
- **Backup API**
  - Получение статуса резервного копирования
  - Обработка 404 при недоступности функции

Покрывает:
- Отправку корректных HTTP-запросов
- Обработку успешных и ошибочных ответов
- Управление состоянием в storage
- Корректную передачу параметров

### Вспомогательные функции (Test Helpers)

#### `tests/utils/testHelpers.js`
Набор утилит для упрощения написания тестов:

- `loadAdminPanelDOM()` - загружает HTML админ-панели в тестовое окружение
- `mockFetch()` - создает мок для fetch API с настраиваемыми ответами
- `mockAdminSession()` - создает объект тестовой сессии админа
- `cleanupDOM()` - очищает DOM после тестов

## Конфигурация

### `vitest.config.js`
Конфигурация Vitest:
- **Environment**: `happy-dom` - легковесная DOM-реализация для тестов
- **Globals**: включены глобальные функции (describe, it, expect)
- **Setup Files**: автоматическая загрузка `tests/setup.js`
- **Coverage**: настроено покрытие кода с отчетами в форматах text, json, html

### `tests/setup.js`
Настройка тестового окружения:
- Моки для `localStorage` и `sessionStorage`
- Автоматическая очистка storage перед каждым тестом
- Глобальные хуки (beforeEach)

## Написание новых тестов

### Пример модульного теста

```javascript
import { describe, it, expect } from 'vitest';

describe('Название модуля', () => {
  it('должен делать что-то конкретное', () => {
    // Arrange - подготовка
    const input = 'test';

    // Act - выполнение
    const result = someFunction(input);

    // Assert - проверка
    expect(result).toBe('expected');
  });
});
```

### Пример интеграционного теста с fetch

```javascript
import { describe, it, expect, vi } from 'vitest';

describe('API Integration', () => {
  it('должен отправлять правильный запрос', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ success: true })
      })
    );

    const result = await myApiFunction();

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/endpoint',
      expect.objectContaining({
        method: 'GET',
        headers: expect.any(Object)
      })
    );
    expect(result).toEqual({ success: true });
  });
});
```

## Лучшие практики

1. **Изолированность тестов** - каждый тест должен быть независимым
2. **Очистка состояния** - используйте `beforeEach` для сброса состояния
3. **Описательные названия** - используйте понятные названия для тестов
4. **Arrange-Act-Assert** - следуйте паттерну организации тестов
5. **Моки для внешних зависимостей** - используйте `vi.fn()` для моков
6. **Проверка граничных случаев** - тестируйте не только happy path

## Покрытие кода

После запуска тестов с покрытием (`npm run test:coverage`) отчет будет доступен в каталоге `coverage/`:
- `coverage/index.html` - визуальный отчет
- `coverage/coverage-final.json` - данные для CI/CD

## Непрерывная интеграция (CI/CD)

Тесты можно интегрировать в CI/CD пайплайн:

```yaml
# Пример для GitHub Actions
- name: Run tests
  run: |
    cd admin
    npm install
    npm test
```

## Отладка тестов

### В режиме отладки
```bash
npx vitest --inspect-brk
```

### С выводом дополнительной информации
```bash
npx vitest --reporter=verbose
```

### Запуск только упавших тестов
```bash
npx vitest --changed
```

## Дополнительные ресурсы

- [Документация Vitest](https://vitest.dev/)
- [API Happy-DOM](https://github.com/capricorn86/happy-dom)
- [Гайд по тестированию JavaScript](https://jestjs.io/docs/getting-started)

## Поддержка

При возникновении вопросов или проблем с тестами:
1. Проверьте, что все зависимости установлены (`npm install`)
2. Убедитесь, что используется актуальная версия Node.js (>=18)
3. Проверьте логи тестов на наличие конкретных ошибок
4. Обратитесь к документации Vitest для решения специфичных проблем
