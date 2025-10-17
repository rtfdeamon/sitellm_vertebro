(function initAdminStaticI18n(global) {
  const STATIC_I18N = {
    text: {
      aiGenerateButton: {
        en: 'Generate with AI',
        ru: 'AI‑сгенерировать',
        match: ['AI‑сгенерировать'],
      },
      activateIntegration: {
        en: 'Activate integration',
        ru: 'Активировать интеграцию',
        match: ['Активировать интеграцию'],
      },
      addButton: {
        en: 'Add',
        ru: 'Добавить',
        match: ['Добавить'],
      },
      addManualButton: {
        en: 'Add manually',
        ru: 'Добавить вручную',
        match: ['Добавить вручную'],
      },
      answerLabel: {
        en: 'Answer',
        ru: 'Ответ',
        match: ['Ответ'],
      },
      autoStartLabel: {
        en: 'Auto-start on launch',
        ru: 'Автозапуск при старте',
        match: ['Автозапуск при старте'],
      },
      automaticModeLabel: {
        en: 'Automatic (when queue is idle)',
        ru: 'Автоматический (при простое очереди)',
        match: ['Автоматический (при простое очереди)'],
      },
      backupLogTitle: {
        en: 'Operations log',
        ru: 'Журнал операций',
        match: ['Журнал операций'],
      },
      buttonClear: {
        en: 'Clear',
        ru: 'Очистить',
        match: ['Очистить'],
      },
      buttonClearList: {
        en: 'Clear list',
        ru: 'Очистить список',
        match: ['Очистить список'],
      },
      buttonCompile: {
        en: 'Compile',
        ru: 'Компилировать',
        match: ['Компилировать'],
      },
      buttonCreate: {
        en: 'Create',
        ru: 'Создать',
        match: ['Создать'],
      },
      buttonReset: {
        en: 'Reset',
        ru: 'Сбросить',
        match: ['Сбросить'],
      },
      buttonSave: {
        en: 'Save',
        ru: 'Сохранить',
        match: ['Сохранить'],
      },
      buttonDelete: {
        en: 'Delete',
        ru: 'Удалить',
        match: ['Удалить'],
      },
      buttonDeleteProject: {
        en: 'Delete project',
        ru: 'Удалить проект',
        match: ['Удалить проект'],
      },
      buttonImport: {
        en: 'Import',
        ru: 'Импортировать',
        match: ['Импортировать'],
      },
      buttonOpenWidget: {
        en: 'Open widget',
        ru: 'Открыть виджет',
        match: ['Открыть виджет'],
      },
      buttonRefreshStatus: {
        en: 'Refresh status',
        ru: 'Обновить статус',
        match: ['Обновить статус'],
      },
      buttonSavePrompt: {
        en: 'Save prompt',
        ru: 'Сохранить промпт',
        match: ['Сохранить промпт'],
      },
      buttonStartProcessing: {
        en: 'Start processing',
        ru: 'Запустить обработку',
        match: ['Запустить обработку'],
      },
      catalogOllamaTitle: {
        en: 'Ollama model catalog',
        ru: 'Каталог моделей Ollama',
        match: ['Каталог моделей Ollama'],
      },
      clusterWarningMessage: {
        en: 'LLM operations are paused. No Ollama servers available.',
        ru: 'Работа с LLM приостановлена. Нет доступных серверов Ollama.',
        match: ['Работа с LLM приостановлена. Нет доступных серверов Ollama.'],
      },
      contextsLabel: {
        en: 'Contexts:',
        ru: 'Контексты:',
        match: ['Контексты:'],
      },
      dangerZoneTitle: {
        en: 'Danger zone',
        ru: 'Опасная зона',
        match: ['Опасная зона'],
      },
      detailedDebugLabel: {
        en: 'Detailed debug after response',
        ru: 'Подробная отладка после ответа',
        match: ['Подробная отладка после ответа'],
      },
      buttonClose: {
        en: 'Close',
        ru: 'Закрыть',
        match: ['Закрыть'],
      },
      documentTitle: {
        en: 'Document',
        ru: 'Документ',
        match: ['Документ'],
      },
      dragFilesHint: {
        en: 'Drag files here or use the field above',
        ru: 'Перетащите файлы сюда или нажмите на поле выше',
        match: ['Перетащите файлы сюда или нажмите на поле выше'],
      },
      emailSignatureLabel: {
        en: 'Email signature',
        ru: 'Подпись в письмах',
        match: ['Подпись в письмах'],
      },
      emotionsLabel: {
        en: 'Emotions and emojis in replies',
        ru: 'Эмоции и эмодзи в ответах',
        match: ['Эмоции и эмодзи в ответах'],
      },
      enableIntegrationButton: {
        en: 'Enable integration',
        ru: 'Включить интеграцию',
        match: ['Включить интеграцию'],
      },
      enabledStatus: {
        en: 'Enabled',
        ru: 'Включён',
        match: ['Включён'],
      },
      imapSslLabel: {
        en: 'IMAP SSL',
        ru: 'IMAP SSL',
        match: ['IMAP SSL'],
      },
      smtpStarttlsLabel: {
        en: 'SMTP STARTTLS',
        ru: 'SMTP STARTTLS',
        match: ['SMTP STARTTLS'],
      },
      llmSectionTitle: {
        en: 'LLM',
        ru: 'LLM',
        match: ['LLM'],
      },
      llmModelLabel: {
        en: 'Model: {value}',
        ru: 'Модель: {value}',
        match: ['Модель: {value}'],
      },
      llmBackendLabel: {
        en: 'Backend: {value}',
        ru: 'Бэкенд: {value}',
        match: ['Бэкенд: {value}'],
      },
      llmDeviceLabel: {
        en: 'Device: {value}',
        ru: 'Устройство: {value}',
        match: ['Устройство: {value}'],
      },
      llmSaveButton: {
        en: 'Save',
        ru: 'Сохранить',
        match: ['Сохранить'],
      },
      llmPingButton: {
        en: 'Ping',
        ru: 'Проверить',
        match: ['Проверить'],
      },
      ollamaBaseLabel: {
        en: 'Ollama Base:',
        ru: 'Адрес Ollama:',
        match: ['Адрес Ollama:'],
      },
      ollamaModelNameLabel: {
        en: 'Model name:',
        ru: 'Название модели:',
        match: ['Название модели:'],
      },
      llmPromptsTitle: {
        en: 'LLM Prompts',
        ru: 'Промпты LLM',
        match: ['Промпты LLM'],
      },
      logsCardTitle: {
        en: 'Logs (last 200)',
        ru: 'Логи (последние 200)',
        match: ['Логи (последние 200)'],
      },
      logCopyButton: {
        en: 'Copy',
        ru: 'Скопировать',
        match: ['Скопировать'],
      },
      labelUrl: {
        en: 'URL',
        ru: 'URL',
        match: ['URL'],
      },
      smtpHostLabel: {
        en: 'SMTP host',
        ru: 'SMTP хост',
        match: ['SMTP хост'],
      },
      smtpPortLabel: {
        en: 'SMTP port',
        ru: 'SMTP порт',
        match: ['SMTP порт'],
      },
      exportCsvButton: {
        en: 'Export CSV',
        ru: 'Экспорт CSV',
        match: ['Экспорт CSV'],
      },
      filesLabel: {
        en: 'Files:',
        ru: 'Файлы:',
        match: ['Файлы:'],
      },
      hintAnswerSources: {
        en: 'Show a list of sources after each answer.',
        ru: 'После ответа будет отображаться список ссылок на использованные материалы.',
        match: ['После ответа будет отображаться список ссылок на использованные материалы.'],
      },
      hintDetailedSummary: {
        en: 'Enable to receive a detailed summary after each answer (tokens, knowledge, session).',
        ru: 'Включите, чтобы после ответа приходила подробная сводка (символы, знания, сессия).',
        match: ['Включите, чтобы после ответа приходила подробная сводка (символы, знания, сессия).'],
      },
      hintMailSettings: {
        en: 'Specify IMAP/SMTP parameters so the assistant can send and read emails.',
        ru: 'Укажите параметры IMAP/SMTP, чтобы ассистент мог отправлять и просматривать письма.',
        match: ['Укажите параметры IMAP/SMTP, чтобы ассистент мог отправлять и просматривать письма.'],
      },
      hintPromptConfig: {
        en: 'Configure the prompt and vector knowledge base refresh mode.',
        ru: 'Настройте промт и режим обновления векторной базы знаний.',
        match: ['Настройте промт и режим обновления векторной базы знаний.'],
      },
      hintProvideAdminCredentials: {
        en: 'Provide the admin login and password for the project.',
        ru: 'Укажите логин и пароль администратора проекта.',
        match: ['Укажите логин и пароль администратора проекта.'],
      },
      hintVoiceAssistant: {
        en: 'Enable to display the animated voice assistant on the site.',
        ru: 'Включите, чтобы показывать анимированного голосового ассистента на сайте.',
        match: ['Включите, чтобы показывать анимированного голосового ассистента на сайте.'],
      },
      hintVoiceCaptions: {
        en: 'LLM will generate short captions when indexing images.',
        ru: 'LLM будет подбирать короткое описание при индексации изображений.',
        match: ['LLM будет подбирать короткое описание при индексации изображений.'],
      },
      hintWarmReplies: {
        en: 'Leave enabled to keep responses warm and lively.',
        ru: 'Оставьте включённым, чтобы ответы были тёплыми и живыми.',
        match: ['Оставьте включённым, чтобы ответы были тёплыми и живыми.'],
      },
      hintWebhook: {
        en: 'Webhook is used for model requests and stored on the server.',
        ru: 'Webhook используется для запросов модели и хранится на сервере.',
        match: ['Webhook используется для запросов модели и хранится на сервере.'],
      },
      identifierLabel: {
        en: 'Identifier (ENG)',
        ru: 'Идентификатор (ENG)',
        match: ['Идентификатор (ENG)'],
      },
      imageCaptionsLabel: {
        en: 'Knowledge base image captions',
        ru: 'Подписи к изображениям базы знаний',
        match: ['Подписи к изображениям базы знаний'],
      },
      imapHostLabel: {
        en: 'IMAP host',
        ru: 'IMAP хост',
        match: ['IMAP хост'],
      },
      imapPortLabel: {
        en: 'IMAP port',
        ru: 'IMAP порт',
        match: ['IMAP порт'],
      },
      installationTitle: {
        en: 'Installation',
        ru: 'Установка',
        match: ['Установка'],
      },
      installedTitle: {
        en: 'Installed',
        ru: 'Установленные',
        match: ['Установленные'],
      },
      integrationMax: {
        en: 'MAX bot',
        ru: 'MAX бот',
        match: ['MAX бот'],
      },
      integrationTelegram: {
        en: 'Telegram bot',
        ru: 'Telegram бот',
        match: ['Telegram бот'],
      },
      integrationVk: {
        en: 'VK bot',
        ru: 'VK бот',
        match: ['VK бот'],
      },
      intelligentProcessingTitle: {
        en: 'Intelligent processing',
        ru: 'Интеллектуальная обработка',
        match: ['Интеллектуальная обработка'],
      },
      knowledgeProjectHint: {
        en: 'Select a project to view data volume.',
        ru: 'Выберите проект, чтобы увидеть объём данных.',
        match: ['Выберите проект, чтобы увидеть объём данных.'],
      },
      knowledgeSearchLabel: {
        en: 'Search',
        ru: 'Поиск',
        match: ['Поиск'],
      },
      knowledgeSectionTitle: {
        en: 'Knowledge Base',
        ru: 'База знаний',
        match: ['База знаний'],
      },
      knowledgeNavLabel: {
        en: 'Knowledge base management',
        ru: 'Управление базой знаний',
        match: [],
      },
      knowledgeCardTitle: {
        en: 'Knowledge Base',
        ru: 'База знаний',
        match: [],
      },
      kbPriorityTitle: {
        en: 'Source priority',
        ru: 'Приоритет источников',
        match: [],
      },
      knowledgeTabUpload: {
        en: 'Upload',
        ru: 'Загрузка',
      },
      knowledgeTabDocuments: {
        en: 'Documents',
        ru: 'Документы',
        match: ['Документы'],
      },
      knowledgeTabOverview: {
        en: 'Overview',
        ru: 'Обзор',
        match: ['Обзор'],
      },
      knowledgeTabQa: {
        en: 'Q&A',
        ru: 'Вопрос–ответ',
        match: ['Вопрос–ответ'],
      },
      knowledgeTabUnanswered: {
        en: 'Unanswered',
        ru: 'Вопросы без ответа',
        match: ['Вопросы без ответа'],
      },
      summaryCrawlerTitle: {
        en: 'Crawling',
        ru: 'Краулинг',
        match: ['Краулинг'],
      },
      summaryResourcesTitle: {
        en: 'Resources',
        ru: 'Ресурсы',
        match: ['Ресурсы'],
      },
      summaryLlmTitle: {
        en: 'LLM insights',
        ru: 'LLM мысли',
        match: ['LLM мысли'],
      },
      summaryBuildTitle: {
        en: 'Build',
        ru: 'Сборка',
        match: ['Сборка'],
      },
      knowledgeThinkingCaption: {
        en: 'Generating description…',
        ru: 'Генерируем описание…',
        match: ['Генерируем описание…'],
      },
      knowledgeThinkingSubtitle: {
        en: 'This may take a few seconds.',
        ru: 'Это может занять несколько секунд.',
        match: ['Это может занять несколько секунд.'],
      },
      knowledgeSourceFaq: {
        en: 'FAQ (Q&A)',
        ru: 'FAQ (Вопрос–ответ)',
      },
      knowledgeSourceVector: {
        en: 'Vector search',
        ru: 'Векторный поиск',
      },
      knowledgeSourceDocsFiles: {
        en: 'Documents and files',
        ru: 'Документы и файлы',
      },
      knowledgeTableTextEmpty: {
        en: 'No text documents',
        ru: 'Текстовые документы отсутствуют',
      },
      knowledgeTableDocsEmpty: {
        en: 'No files found',
        ru: 'Файлы не найдены',
      },
      knowledgeTableImagesEmpty: {
        en: 'No images',
        ru: 'Нет изображений',
      },
      knowledgeAutoDescriptionPending: {
        en: 'Description in progress',
        ru: 'Описание формируется',
      },
      knowledgeAutoDescriptionFailed: {
        en: 'Auto description failed',
        ru: 'Автоописание не удалось',
      },
      knowledgeAutoDescriptionLabel: {
        en: 'Auto description: {value}',
        ru: 'Автоописание: {value}',
      },
      knowledgeBadgePhoto: {
        en: 'Photo',
        ru: 'Фото',
      },
      knowledgeBadgeFile: {
        en: 'File',
        ru: 'Файл',
      },
      buttonDownload: {
        en: 'Download',
        ru: 'Скачать',
      },
      buttonEdit: {
        en: 'Edit',
        ru: 'Редактировать',
      },
      tooltipEditDescription: {
        en: 'Edit description and metadata',
        ru: 'Изменить описание и метаданные',
      },
      knowledgePriorityUnavailable: {
        en: 'Knowledge priorities unavailable',
        ru: 'Приоритеты недоступны',
      },
      knowledgePriorityLoadError: {
        en: 'Failed to load priorities',
        ru: 'Не удалось загрузить приоритеты',
      },
      knowledgePrioritySaving: {
        en: 'Saving…',
        ru: 'Сохраняем...',
      },
      knowledgePrioritySaveUnavailable: {
        en: 'Save unavailable',
        ru: 'Сохранение недоступно',
      },
      knowledgePrioritySaved: {
        en: 'Priorities updated',
        ru: 'Приоритеты обновлены',
      },
      knowledgePrioritySaveError: {
        en: 'Failed to save priorities',
        ru: 'Не удалось сохранить приоритеты',
      },
      knowledgeDropSummary: {
        en: 'Selected files: {count}. {preview}{remaining}',
        ru: 'Выбрано файлов: {count}. {preview}{remaining}',
      },
      serviceStateOn: {
        en: 'Service enabled',
        ru: 'Сервис включён',
      },
      serviceStateOff: {
        en: 'Service disabled',
        ru: 'Сервис выключен',
      },
      serviceStateLabelOn: {
        en: 'Service: enabled',
        ru: 'Сервис: включён',
      },
      serviceStateLabelOff: {
        en: 'Service: disabled',
        ru: 'Сервис: выключен',
      },
      serviceModeLabel: {
        en: 'Mode: {value}',
        ru: 'Режим: {value}',
      },
      serviceStatusActive: {
        en: 'Status: active',
        ru: 'Статус: активен',
      },
      serviceStatusStopped: {
        en: 'Status: stopped',
        ru: 'Статус: остановлен',
      },
      serviceModeAuto: {
        en: 'automatic',
        ru: 'автоматический',
      },
      serviceModeManual: {
        en: 'manual',
        ru: 'ручной',
      },
      knowledgeProcessingStarting: {
        en: 'Starting processing…',
        ru: 'Запускаем обработку…',
      },
      knowledgeProcessingDone: {
        en: 'Processing completed',
        ru: 'Обработка завершена',
      },
      knowledgeProcessingFailed: {
        en: 'Processing completed with error',
        ru: 'Обработка завершена с ошибкой',
      },
      knowledgeProcessingStartError: {
        en: 'Failed to start processing',
        ru: 'Ошибка запуска обработки',
      },
      knowledgeQueueLabel: {
        en: 'Queue: {value}',
        ru: 'Очередь: {value}',
      },
      knowledgeIdleLabel: {
        en: 'Idle: {seconds} s',
        ru: 'Простой: {seconds} с',
      },
      knowledgeLastRunLabel: {
        en: 'Last run: {value}',
        ru: 'Последний запуск: {value}',
      },
      knowledgeErrorLabel: {
        en: 'Error: {value}',
        ru: 'Ошибка: {value}',
      },
      knowledgeReasonLabel: {
        en: 'Reason: {value}',
        ru: 'Причина: {value}',
      },
      knowledgeUpdatedLabel: {
        en: 'Updated: {value}',
        ru: 'Обновлено: {value}',
      },
      loadingEllipsis: {
        en: 'Loading…',
        ru: 'Загрузка…',
      },
      projectsRoleFriendlyLabel: {
        en: 'Friendly expert',
        ru: 'Дружелюбный эксперт',
      },
      projectsRoleFriendlyHint: {
        en: 'Warm tone, supporting the client and their goals.',
        ru: 'Тёплый тон, поддержка клиента и забота о его задачах.',
      },
      projectsRoleFormalLabel: {
        en: 'Formal consultant',
        ru: 'Формальный консультант',
      },
      projectsRoleFormalHint: {
        en: 'Business style focused on facts and regulations.',
        ru: 'Деловой стиль общения, акцент на фактах и регламентах.',
      },
      projectsRoleManagerLabel: {
        en: 'Active manager',
        ru: 'Активный менеджер',
      },
      projectCardTitle: {
        en: 'Project',
        ru: 'Проект',
      },
      projectMenuTitle: {
        en: 'Project menu',
        ru: 'Проектное меню',
      },
      feedbackSectionTitle: {
        en: 'Feedback',
        ru: 'Отзывы',
      },
      feedbackNoItems: {
        en: 'No feedback yet.',
        ru: 'Отзывов пока нет.',
      },
      projectDomainHint: {
        en: 'Paste full URL, for example https://example.com',
        ru: 'Вставьте полный адрес, например https://example.com',
      },
      projectsRoleManagerHint: {
        en: 'Focus on product benefits and gentle sales.',
        ru: 'Фокус на выгодах продукта и мягких продажах.',
      },
      projectsSelectForStorage: {
        en: 'Select a project to view storage details.',
        ru: 'Выберите проект, чтобы увидеть объём данных.',
      },
      projectsOpenWidget: {
        en: 'Open widget',
        ru: 'Открыть виджет',
      },
      projectsWidgetNoProject: {
        en: 'Link appears after selecting a project',
        ru: 'Ссылка отображается после выбора проекта',
      },
      projectsKeepEmpty: {
        en: 'Leave empty to keep unchanged',
        ru: 'Оставьте пустым, чтобы не менять',
      },
      projectsDomainLabel: {
        en: 'Domain: {value}',
        ru: 'Домен: {value}',
      },
      projectsModelLabel: {
        en: 'Model: {value}',
        ru: 'Модель: {value}',
      },
      projectsVoiceModelLabel: {
        en: 'Voice model: {value}',
        ru: 'Голосовая модель: {value}',
      },
      projectsStoppedByInput: {
        en: 'Stopped: user input',
        ru: 'Остановлено: ввод пользователя',
      },
      projectsStopped: {
        en: 'Stopped',
        ru: 'Остановлено',
      },
      projectsSelectForActivity: {
        en: 'Select a project to view activity',
        ru: 'Выберите проект, чтобы увидеть активность',
      },
      projectsEmotionsOn: {
        en: 'Emotions: on',
        ru: 'Эмоции: вкл',
      },
      projectsEmotionsOff: {
        en: 'Emotions: off',
        ru: 'Эмоции: выкл',
      },
      projectsHelpOn: {
        en: 'Pre-answer brief: on',
        ru: 'Справка: вкл',
      },
      projectsHelpOff: {
        en: 'Pre-answer brief: off',
        ru: 'Справка: выкл',
      },
      projectsDebugOn: {
        en: 'Debug: on',
        ru: 'Отладка: вкл',
      },
      projectsDebugOff: {
        en: 'Debug: off',
        ru: 'Отладка: выкл',
      },
      projectsSourcesOn: {
        en: 'Sources: on',
        ru: 'Источники: вкл',
      },
      projectsSourcesOff: {
        en: 'Sources: off',
        ru: 'Источники: выкл',
      },
      projectsCaptionsOn: {
        en: 'Image captions: on',
        ru: 'Подписи изображений: вкл',
      },
      projectsCaptionsOff: {
        en: 'Image captions: off',
        ru: 'Подписи изображений: выкл',
      },
      projectsVoiceModeOn: {
        en: 'Voice mode: on',
        ru: 'Голосовой режим: вкл',
      },
      projectsVoiceModeOff: {
        en: 'Voice mode: off',
        ru: 'Голосовой режим: выкл',
      },
      projectsAwaitingActivity: {
        en: 'Waiting for model activity',
        ru: 'Ожидаем активности модели',
      },
      projectsStorageUnavailable: {
        en: 'Storage data unavailable.',
        ru: 'Данные о хранилище недоступны.',
      },
      projectsWidgetCustomLink: {
        en: 'Saved link is used',
        ru: 'Используется сохранённая ссылка',
      },
      projectsWidgetDefault: {
        en: 'Default: {path}',
        ru: 'По умолчанию: {path}',
      },
      projectsCopied: {
        en: 'Copied',
        ru: 'Скопировано',
      },
      projectsCopyFailed: {
        en: 'Copy failed',
        ru: 'Не удалось скопировать',
      },
      projectsEmotionsOnHint: {
        en: 'Responses stay warm and may include emojis.',
        ru: 'Ответы будут тёплыми и могут включать эмодзи.',
      },
      projectsEmotionsOffHint: {
        en: 'Responses will be neutral without emojis.',
        ru: 'Ответы будут нейтральными без эмодзи.',
      },
      projectsWidgetVoiceHintOn: {
        en: 'The widget can display an animated voice assistant.',
        ru: 'Виджет может показывать анимированного голосового ассистента.',
      },
      projectsWidgetVoiceHintOff: {
        en: 'The voice assistant will not appear in the widget.',
        ru: 'Голосовой консультант не будет доступен в виджете.',
      },
      projectsCaptionsHint: {
        en: 'The LLM creates short captions for knowledge base images during indexing.',
        ru: 'LLM создаёт короткие подписи для изображений при индексации.',
      },
      projectsCaptionsOffHint: {
        en: 'Captions are not generated; images are stored without descriptions.',
        ru: 'Подписи не генерируются, изображения сохраняются без описания.',
      },
      projectsSourcesOnHint: {
        en: 'After each answer the bot shows links to the sources used.',
        ru: 'После каждого ответа бот покажет ссылки на использованные материалы.',
      },
      projectsSourcesOffHint: {
        en: 'The list of sources will stay hidden unless the user explicitly asks for it.',
        ru: 'Список источников будет скрыт, если пользователь явно не попросит о нём.',
      },
      projectsDebugInfoOnHint: {
        en: 'Before every answer the bot sends an internal briefing about the request.',
        ru: 'Перед каждым ответом бот отправит служебную справку о запросе.',
      },
      projectsDebugInfoOffHint: {
        en: 'The pre-answer briefing is disabled.',
        ru: 'Служебная справка перед ответом отключена.',
      },
      projectsDebugOnHint: {
        en: 'After each answer the bot sends a detailed summary (tokens, knowledge, session).',
        ru: 'После ответа будет приходить подробная сводка (символы, знания, сессия).',
      },
      projectsDebugOffHint: {
        en: 'The final debug summary is disabled.',
        ru: 'Финальная отладочная сводка отключена.',
      },
      projectsStorageSummary: {
        en: 'Storage: texts {text} · files {files} · contexts {contexts} · Redis {redis}',
        ru: 'Хранилище: тексты {text} · файлы {files} · контексты {contexts} · Redis {redis}',
      },
      projectsRemovedDocuments: {
        en: 'documents: {value}',
        ru: 'документов: {value}',
      },
      projectsRemovedFiles: {
        en: 'files: {value}',
        ru: 'файлов: {value}',
      },
      projectsRemovedContexts: {
        en: 'contexts: {value}',
        ru: 'контекстов: {value}',
      },
      projectsRemovedStats: {
        en: 'stats entries: {value}',
        ru: 'записей статистики: {value}',
      },
      projectsRemovedSummary: {
        en: 'Removed ({value})',
        ru: 'Удалено ({value})',
      },
      projectsDeleteDocuments: {
        en: 'documents: {value}',
        ru: 'документов: {value}',
      },
      projectsDeleteContexts: {
        en: 'contexts: {value}',
        ru: 'контекстов: {value}',
      },
      projectsDeleteRedisKeys: {
        en: 'Redis keys: {value}',
        ru: 'ключей Redis: {value}',
      },
      projectsDeleteTextsSize: {
        en: 'texts: {value}',
        ru: 'тексты: {value}',
      },
      projectsDeleteFilesSize: {
        en: 'files: {value}',
        ru: 'файлы: {value}',
      },
      projectsDeleteContextsSize: {
        en: 'contexts: {value}',
        ru: 'контексты: {value}',
      },
      projectsDeleteRedisSize: {
        en: 'Redis: {value}',
        ru: 'Redis: {value}',
      },
      projectsDeleteConfirm: {
        en: 'Delete project {project}?',
        ru: 'Удалить проект {project}?',
      },
      projectsAdminCredentialsHint: {
        en: 'Enter the admin login and password for the project.',
        ru: 'Укажите логин и пароль администратора проекта.',
      },
      ollamaJobPending: {
        en: 'Pending',
        ru: 'Ожидает запуска',
      },
      ollamaJobRunning: {
        en: 'Installing…',
        ru: 'Установка выполняется',
      },
      ollamaJobSuccess: {
        en: 'Installed',
        ru: 'Установка завершена',
      },
      ollamaJobError: {
        en: 'Installation failed',
        ru: 'Ошибка установки',
      },
      ollamaInstalledEmpty: {
        en: 'No models installed.',
        ru: 'Нет установленных моделей.',
      },
      ollamaPopularEmpty: {
        en: 'No recommended models.',
        ru: 'Нет рекомендованных моделей.',
      },
      ollamaJobsEmpty: {
        en: 'No active installations.',
        ru: 'Нет активных установок.',
      },
      ollamaCatalogUnavailable: {
        en: 'Catalog unavailable: ollama command not found, but models detected.',
        ru: 'Каталог недоступен: команда ollama не найдена, но модели обнаружены.',
      },
      ollamaCommandMissing: {
        en: 'Ollama command not found on the server.',
        ru: 'Команда ollama не найдена на сервере.',
      },
      ollamaCatalogRefreshing: {
        en: 'Refreshing catalog…',
        ru: 'Обновляем каталог…',
      },
      ollamaCatalogSummary: {
        en: 'Ollama command available. Models installed: {count}.',
        ru: 'Команда Ollama доступна. Установлено моделей: {count}.',
      },
      ollamaCatalogLoadError: {
        en: 'Failed to load catalog: {error}',
        ru: 'Не удалось загрузить каталог: {error}',
      },
      ollamaRefreshError: {
        en: 'Refresh error: {error}',
        ru: 'Ошибка загрузки: {error}',
      },
      ollamaRefreshUpdating: {
        en: 'Refreshing list…',
        ru: 'Обновляем список…',
      },
      ollamaServersNone: {
        en: 'No servers configured.',
        ru: 'Не настроено ни одного сервера.',
      },
      ollamaServersEmpty: {
        en: 'No Ollama servers registered.',
        ru: 'Нет зарегистрированных серверов Ollama.',
      },
      ollamaServerSaving: {
        en: 'Saving server…',
        ru: 'Сохраняем сервер…',
      },
      ollamaServerSaved: {
        en: 'Server saved.',
        ru: 'Сервер сохранён.',
      },
      ollamaServerDeleting: {
        en: 'Deleting server…',
        ru: 'Удаляем сервер…',
      },
      ollamaServerDeleted: {
        en: 'Server deleted.',
        ru: 'Сервер удалён.',
      },
      ollamaServerUpdatingState: {
        en: 'Updating server state…',
        ru: 'Включаем сервер…',
      },
      ollamaServerDisabling: {
        en: 'Disabling server…',
        ru: 'Выключаем сервер…',
      },
      ollamaServerUpdated: {
        en: 'Server state updated.',
        ru: 'Состояние сервера обновлено.',
      },
      ollamaServerFormInvalid: {
        en: 'Specify server name and address.',
        ru: 'Укажите имя и адрес сервера.',
      },
      ollamaServerStatusTitle: {
        en: 'Status',
        ru: 'Статус',
      },
      ollamaLatencyLabel: {
        en: 'Latency',
        ru: 'Латентность',
      },
      ollamaRequestsPerHour: {
        en: 'Requests/hour',
        ru: 'Запросов/час',
      },
      ollamaInFlight: {
        en: 'In flight',
        ru: 'В работе',
      },
      ollamaLatencyValue: {
        en: '{value} ms',
        ru: '{value} мс',
      },
      ollamaServersSummary: {
        en: 'Total: {total}. Enabled: {enabled}. Available: {active}.',
        ru: 'Всего: {total}. Включены: {enabled}. Доступны: {active}.',
      },
      ollamaServerEnabled: {
        en: 'Enabled',
        ru: 'Включён',
      },
      ollamaServerDisabled: {
        en: 'Disabled',
        ru: 'выключен',
      },
      ollamaServerHealthy: {
        en: 'healthy',
        ru: 'активен',
      },
      ollamaServerError: {
        en: 'error',
        ru: 'ошибка',
      },
      ollamaServerHealthyUnknown: {
        en: 'unknown',
        ru: 'нет сведений',
      },
      ollamaServerUpdatedAt: {
        en: 'updated {value}',
        ru: 'обновлена {value}',
      },
      ollamaServerInstallStarted: {
        en: 'Model {model} installation started.',
        ru: 'Установка модели {model} запущена.',
      },
      ollamaInstallButton: {
        en: 'Install',
        ru: 'Установить',
      },
      ollamaInstalling: {
        en: 'Installing…',
        ru: 'Устанавливаем…',
      },
      ollamaButtonDelete: {
        en: 'Delete',
        ru: 'Удалить',
      },
      ollamaServerToggleOn: {
        en: 'Enabled',
        ru: 'Включён',
      },
      ollamaServerToggleOff: {
        en: 'Disabled',
        ru: 'выключен',
      },
      ollamaServerDefaultTitle: {
        en: 'Default',
        ru: 'По умолчанию',
      },
      ollamaServerUnnamed: {
        en: 'Unnamed',
        ru: 'Без названия',
      },
      ollamaServerErrorLabel: {
        en: 'Error: {value}',
        ru: 'Ошибка: {value}',
      },
      ollamaActionSaveError: {
        en: 'Save error: {error}',
        ru: 'Ошибка сохранения: {error}',
      },
      ollamaActionDeleteError: {
        en: 'Delete error: {error}',
        ru: 'Ошибка удаления: {error}',
      },
      ollamaActionUpdateError: {
        en: 'Update error: {error}',
        ru: 'Ошибка обновления: {error}',
      },
      ollamaActionInstallError: {
        en: 'Install error: {error}',
        ru: 'Ошибка установки: {error}',
      },
      ollamaActionGeneralError: {
        en: 'Error: {error}',
        ru: 'Ошибка: {error}',
      },
      voiceSelectProjectForRecording: {
        en: 'Select a project to record.',
        ru: 'Выберите проект для записи.',
      },
      voiceSelectProjectForTraining: {
        en: 'Select a project to start training.',
        ru: 'Выберите проект для обучения.',
      },
      voiceSelectProjectToAddSample: {
        en: 'Select a project to add a recording.',
        ru: 'Выберите проект, чтобы добавить запись.',
      },
      voiceSelectProjectToUpload: {
        en: 'Select a project to upload samples.',
        ru: 'Выберите проект, чтобы загрузить дорожки.',
      },
      voiceSelectFilesPrompt: {
        en: 'Select files to upload.',
        ru: 'Выберите файлы для загрузки.',
      },
      voiceDone: {
        en: 'Done',
        ru: 'Готово',
      },
      voiceAddMoreSamples: {
        en: 'Add more samples',
        ru: 'Добавьте ещё дорожки',
      },
      voiceMicDenied: {
        en: 'Microphone access denied.',
        ru: 'Доступ к микрофону запрещён.',
      },
      voiceMinSamplesRemaining: {
        en: 'Upload at least {min} samples. Remaining: {remaining}.',
        ru: 'Загрузите как минимум {min} дорожки. Осталось добавить {remaining}.',
      },
      voiceMinSamplesRequired: {
        en: 'Upload at least 3 samples.',
        ru: 'Загрузите как минимум 3 дорожки.',
      },
      voiceUploadRecording: {
        en: 'Uploading recording…',
        ru: 'Загрузка записи…',
      },
      voiceLoading: {
        en: 'Loading…',
        ru: 'Загрузка…',
      },
      voiceRecordButton: {
        en: 'Record sample',
        ru: 'Записать дорожку',
      },
      voiceRecordingSeconds: {
        en: 'Recording {seconds} s',
        ru: 'Запись {seconds} с',
      },
      voiceRecordingUploaded: {
        en: 'Recording uploaded',
        ru: 'Запись загружена',
      },
      voiceRecordingUnsupported: {
        en: 'Recording is not supported in this browser.',
        ru: 'Запись не поддерживается в этом браузере.',
      },
      voiceHistoryEmpty: {
        en: 'Training history will appear after the first run.',
        ru: 'История запусков появится после обучения.',
      },
      voiceTrainingLoadError: {
        en: 'Failed to load training data.',
        ru: 'Не удалось загрузить данные по голосовому обучению.',
      },
      voiceRecordingLoadError: {
        en: 'Failed to load recording.',
        ru: 'Не удалось загрузить запись',
      },
      voiceTrainingStartError: {
        en: 'Failed to start training.',
        ru: 'Не удалось запустить обучение',
      },
      voiceRecordingStartError: {
        en: 'Failed to start recording.',
        ru: 'Не удалось начать запись.',
      },
      voiceTrainingStarted: {
        en: 'Training started',
        ru: 'Обучение запущено',
      },
      voiceTrainingAlreadyRunning: {
        en: 'Training is already running',
        ru: 'Обучение уже выполняется',
      },
      voiceStopRecording: {
        en: 'Stop recording',
        ru: 'Остановить запись',
      },
      voiceRecordingError: {
        en: 'Recording error.',
        ru: 'Ошибка записи.',
      },
      voiceUploadError: {
        en: 'Failed to upload samples',
        ru: 'Ошибка при загрузке дорожек',
      },
      voiceTrainingRestart: {
        en: 'Restarting training',
        ru: 'Перезапускаем обучение',
      },
      voiceMicPreparing: {
        en: 'Preparing microphone…',
        ru: 'Подготовка микрофона…',
      },
      voicePreparing: {
        en: 'Preparing…',
        ru: 'Подготовка…',
      },
      voiceUploadPending: {
        en: 'Please wait until the upload finishes.',
        ru: 'Подождите окончания загрузки.',
      },
      voiceSamplesReady: {
        en: 'Enough samples collected. You can start training.',
        ru: 'Собрано достаточно дорожек. Можно запускать обучение.',
      },
      voiceDeleteSample: {
        en: 'Delete',
        ru: 'Удалить',
      },
      projectsPasswordPrompt: {
        en: 'Enter new password',
        ru: 'Введите новый пароль',
      },
      projectsAdminSelectHint: {
        en: 'Select a project to manage credentials.',
        ru: 'Выберите проект, чтобы управлять учётными данными.',
      },
      projectsAdminPasswordSet: {
        en: 'A password is set. Leave the field empty to keep it unchanged.',
        ru: 'Пароль настроен. Оставьте поле пустым, чтобы не менять.',
      },
      projectsAdminPasswordChange: {
        en: 'Enter a new password to replace the current one.',
        ru: 'Введите новый пароль, чтобы сменить текущий.',
      },
      projectsAdminPasswordSetup: {
        en: 'Set a password to access the project admin panel.',
        ru: 'Установите пароль для доступа к админке проекта.',
      },
      projectsLoadFailed: {
        en: 'Failed to load projects',
        ru: 'Не удалось загрузить проекты',
      },
      projectsEmptyPlaceholder: {
        en: '— no projects —',
        ru: '— нет проектов —',
      },
      projectsSelectPlaceholder: {
        en: '— select a project —',
        ru: '— выберите проект —',
      },
      projectsLoadError: {
        en: 'Project loading error',
        ru: 'Ошибка загрузки проектов',
      },
      projectsEnterIdentifier: {
        en: 'Enter identifier',
        ru: 'Укажите идентификатор',
      },
      projectsSaving: {
        en: 'Saving project…',
        ru: 'Сохраняем проект...',
      },
      projectsSaveFailed: {
        en: 'Failed to save project',
        ru: 'Не удалось сохранить проект',
      },
      projectsSaved: {
        en: 'Saved',
        ru: 'Сохранено',
      },
      projectsSaveError: {
        en: 'Save error',
        ru: 'Ошибка сохранения',
      },
      projectsDeleteFailed: {
        en: 'Failed to delete',
        ru: 'Не удалось удалить',
      },
      projectsDeleted: {
        en: 'Deleted',
        ru: 'Удалено',
      },
      projectsDeleteError: {
        en: 'Deletion error',
        ru: 'Ошибка удаления',
      },
      reloadProjects: {
        en: 'Reload',
        ru: 'Обновить',
        match: ['Обновить'],
      },
      projectsSelectProject: {
        en: 'Select a project',
        ru: 'Выберите проект',
      },
      projectsTestingServices: {
        en: 'Testing services…',
        ru: 'Тестируем сервисы...',
      },
      projectsTestError: {
        en: 'Test error',
        ru: 'Ошибка теста',
      },
      overviewProjectMeta: {
        en: 'No project selected',
        ru: 'Нет выбранного проекта',
      },
      crawlerStatusScanning: {
        en: 'Scanning ({value})',
        ru: 'Сканирование ({value})',
      },
      crawlerStatusQueuedDetailed: {
        en: 'Queued ({value})',
        ru: 'В очереди ({value})',
      },
      crawlerProgressCounters: {
        en: '{completed} / {total} pages',
        ru: '{completed} / {total} страниц',
      },
      crawlerProgressCountersFailed: {
        en: '{base} · errors: {failed}',
        ru: '{base} · ошибок: {failed}',
      },
      crawlerLastUrlLabel: {
        en: 'Last URL: {value}',
        ru: 'Последний URL: {value}',
      },
      crawlerLastRun: {
        en: 'Last run: {value}',
        ru: 'Последний запуск: {value}',
      },
      crawlerFetchError: {
        en: 'Failed to fetch crawler data',
        ru: 'Не удалось получить данные о краулере',
      },
      crawlerStatusError: {
        en: 'Status error',
        ru: 'Ошибка статуса',
      },
      crawlerErrorsShort: {
        en: 'Errors',
        ru: 'Ошибки',
      },
      crawlerDoneShort: {
        en: 'Done',
        ru: 'Готово',
      },
      crawlerLogsEmptyState: {
        en: 'Crawler logs are empty.',
        ru: 'Логи краулера пока пусты.',
      },
      crawlerLogsLoadError: {
        en: 'Failed to load crawler logs',
        ru: 'Не удалось загрузить логи краулера',
      },
      crawlerLogsLoading: {
        en: 'Loading…',
        ru: 'Загружаем…',
      },
      crawlerActionProcessing: {
        en: 'Processing…',
        ru: 'Выполняем…',
      },
      crawlerActionExecuteError: {
        en: 'Failed to execute action',
        ru: 'Не удалось выполнить действие',
      },
      projectsNoData: {
        en: 'No data',
        ru: 'Нет данных',
      },
      crawlerSelectProjectHint: {
        en: 'Select a project on the left',
        ru: 'Выберите проект слева',
      },
      crawlerStatusFetchFailed: {
        en: 'Failed to fetch crawler status',
        ru: 'Не удалось получить статус краулера',
      },
      crawlerGenericError: {
        en: 'Error',
        ru: 'Ошибка',
      },
      crawlerStarting: {
        en: 'Starting…',
        ru: 'Запускаем...',
      },
      crawlerStarted: {
        en: 'Crawler started',
        ru: 'Краулер запущен',
      },
      crawlerStartFailed: {
        en: 'Failed to start crawler',
        ru: 'Не удалось запустить краулер',
      },
      crawlerStoppedByRequest: {
        en: 'Stopped on request',
        ru: 'Остановлено по запросу',
      },
      crawlerStopping: {
        en: 'Stopping…',
        ru: 'Останавливаем…',
      },
      crawlerStopFailed: {
        en: 'Failed to stop crawler',
        ru: 'Не удалось остановить краулер',
      },
      crawlerStopError: {
        en: 'Failed to stop',
        ru: 'Не удалось остановить',
      },
      crawlerActionReset: {
        en: 'Counters reset',
        ru: 'Счётчики сброшены',
      },
      crawlerActionDedup: {
        en: 'Duplicates removed',
        ru: 'Дубликаты удалены',
      },
      knowledgeQaUploadHint: {
        en: 'Excel file with columns “Question” and “Answer”',
        ru: 'Excel файл с колонками «Вопрос» и «Ответ»',
        match: ['Excel файл с колонками «Вопрос» и «Ответ»'],
      },
      knowledgeButtonClearAll: {
        en: 'Clear knowledge base',
        ru: 'Очистить базу',
        match: ['Очистить базу'],
      },
      knowledgeButtonDeduplicate: {
        en: 'Remove duplicates',
        ru: 'Очистить дубликаты',
        match: ['Очистить дубликаты'],
      },
      voiceUploadButtonText: {
        en: 'Upload clips',
        ru: 'Загрузить дорожки',
        match: ['Загрузить дорожки'],
      },
      voiceRecordButtonText: {
        en: 'Record clip',
        ru: 'Записать дорожку',
        match: ['Записать дорожку'],
      },
      labelAdminLogin: {
        en: 'Admin login',
        ru: 'Админ логин',
        match: ['Админ логин'],
      },
      labelAdminPassword: {
        en: 'Administrator password',
        ru: 'Пароль администратора',
        match: ['Пароль администратора'],
      },
      labelAnswerSources: {
        en: 'Show answer sources',
        ru: 'Показывать источники ответов',
        match: ['Показывать источники ответов'],
      },
      labelCount: {
        en: 'Count',
        ru: 'Количество',
        match: ['Количество'],
      },
      labelDescription: {
        en: 'Description',
        ru: 'Описание',
        match: ['Описание'],
      },
      labelDomain: {
        en: 'Domain',
        ru: 'Домен',
        match: ['Домен'],
      },
      labelDomainOptional: {
        en: 'Domain (optional)',
        ru: 'Домен (необязательно)',
        match: ['Домен (необязательно)'],
      },
      labelFile: {
        en: 'File',
        ru: 'Файл',
        match: ['Файл'],
      },
      labelImages: {
        en: 'Images',
        ru: 'Фото',
        match: ['Фото'],
      },
      labelLastTime: {
        en: 'Last time',
        ru: 'Последний раз',
        match: ['Последний раз'],
      },
      labelLlmModel: {
        en: 'LLM model',
        ru: 'LLM модель',
        match: ['LLM модель'],
      },
      labelMailConnector: {
        en: 'Mail connector',
        ru: 'Почтовый коннектор',
        match: ['Почтовый коннектор'],
      },
      labelModeManual: {
        en: 'Manual (on demand)',
        ru: 'Ручной (по команде)',
        match: ['Ручной (по команде)'],
      },
      labelNewPassword: {
        en: 'New password',
        ru: 'Новый пароль',
        match: ['Новый пароль'],
      },
      labelName: {
        en: 'Name',
        ru: 'Имя',
        match: ['Имя'],
      },
      labelPassword: {
        en: 'Password',
        ru: 'Пароль',
        match: ['Пароль'],
      },
      labelPriority: {
        en: 'Priority',
        ru: 'Приоритет',
        match: ['Приоритет'],
      },
      labelProcessingPrompt: {
        en: 'Processing prompt',
        ru: 'Промт обработки',
        match: ['Промт обработки'],
      },
      labelProject: {
        en: 'Project',
        ru: 'Проект',
        match: ['Проект'],
      },
      labelProjectName: {
        en: 'Project name',
        ru: 'Название проекта',
        match: ['Название проекта'],
      },
      labelPrompt: {
        en: 'Initial prompt',
        ru: 'Стартовый промпт',
        match: ['Стартовый промпт'],
      },
      labelQuestion: {
        en: 'Question',
        ru: 'Вопрос',
        match: ['Вопрос'],
      },
      labelRunMode: {
        en: 'Run mode',
        ru: 'Режим запуска',
        match: ['Режим запуска'],
      },
      labelSender: {
        en: 'Sender (From)',
        ru: 'Отправитель (From)',
        match: ['Отправитель (From)'],
      },
      labelServiceEnabled: {
        en: 'Service enabled',
        ru: 'Сервис включён',
        match: ['Сервис включён'],
      },
      labelServiceNote: {
        en: 'Pre-answer service note',
        ru: 'Служебная справка перед ответом',
        match: ['Служебная справка перед ответом'],
      },
      labelServers: {
        en: 'Servers',
        ru: 'Серверы',
        match: ['Серверы'],
      },
      labelTest: {
        en: 'Test',
        ru: 'Тест',
        match: ['Тест'],
      },
      labelText: {
        en: 'Text',
        ru: 'Текст',
        match: ['Текст'],
      },
      labelTexts: {
        en: 'Prompts:',
        ru: 'Тексты:',
        match: ['Тексты:'],
      },
      labelTitle: {
        en: 'Title',
        ru: 'Название',
        match: ['Название'],
      },
      labelUsername: {
        en: 'Username',
        ru: 'Имя пользователя',
        match: ['Имя пользователя'],
      },
      tableActions: {
        en: 'Actions',
        ru: 'Действия',
        match: ['Действия'],
      },
      labelWidget: {
        en: 'Widget',
        ru: 'Виджет',
        match: ['Виджет'],
      },
      labelWidgetLink: {
        en: 'Widget link',
        ru: 'Ссылка на виджет',
        match: ['Ссылка на виджет'],
      },
      latestRequestsTitle: {
        en: 'Latest requests (including knowledge base)',
        ru: 'Последние запросы (с учётом базы знаний)',
        match: ['Последние запросы (с учётом базы знаний)'],
      },
      modelVoiceOptional: {
        en: 'Voice mode model (optional)',
        ru: 'Модель для голосового режима (опционально)',
        match: ['Модель для голосового режима (опционально)'],
      },
      newProjectTitle: {
        en: 'New project',
        ru: 'Новый проект',
        match: ['Новый проект'],
      },
      noClipsUploaded: {
        en: 'No clips uploaded.',
        ru: 'Дорожки не загружены.',
        match: ['Дорожки не загружены.'],
      },
      noRecordsText: {
        en: 'No records yet.',
        ru: 'Пока нет записей.',
        match: ['Пока нет записей.'],
      },
      popularTitle: {
        en: 'Popular',
        ru: 'Популярные',
        match: ['Популярные'],
      },
      prePromptHint: {
        en: 'Enable to send a service summary before the answer in Telegram (endpoint, emotions, etc.).',
        ru: 'Включите, чтобы перед ответом в Telegram приходила служебная справка (endpoint, эмоции и т. п.).',
        match: ['Включите, чтобы перед ответом в Telegram приходила служебная справка (endpoint, эмоции и т. п.).'],
      },
      questionPairsLabel: {
        en: 'Total pairs:',
        ru: 'Всего пар:',
        match: ['Всего пар:'],
      },
      startWaiting: {
        en: 'Waiting to start',
        ru: 'Ожидание запуска',
        match: ['Ожидание запуска'],
      },
      statsLast14Days: {
        en: 'Last 14 days',
        ru: 'Последние 14 дней',
        match: ['Последние 14 дней'],
      },
      statisticsTitle: {
        en: 'User activity',
        ru: 'Активность пользователей',
        match: ['Активность пользователей'],
      },
      summaryUnanswered: {
        en: 'Total unanswered questions:',
        ru: 'Всего вопросов без ответа:',
        match: ['Всего вопросов без ответа:'],
      },
      knowledgeUnansweredLoadError: {
        en: 'Failed to load unanswered questions.',
        ru: 'Не удалось загрузить вопросы без ответа.',
        match: [],
      },
      knowledgeUnansweredClearing: {
        en: 'Clearing the list…',
        ru: 'Очищаем список…',
        match: [],
      },
      knowledgeUnansweredCleared: {
        en: 'Removed {value} unanswered questions.',
        ru: 'Удалено {value} вопросов без ответа.',
        match: [],
      },
      knowledgeUnansweredClearError: {
        en: 'Failed to clear unanswered questions.',
        ru: 'Не удалось очистить список вопросов без ответа.',
        match: [],
      },
      knowledgeUnansweredClearConfirm: {
        en: 'Clear all unanswered questions?',
        ru: 'Очистить список вопросов без ответа?',
        match: [],
      },
      userFlowHint: {
        en: 'Questions older than 30 days are removed automatically.',
        ru: 'Вопросы старше 30 дней удаляются автоматически.',
        match: ['Вопросы старше 30 дней удаляются автоматически.'],
      },
      voiceAssistantLabel: {
        en: 'Voice assistant',
        ru: 'Голосовой консультант',
        match: ['Голосовой консультант'],
      },
      warningProjectDeletion: {
        en: 'Deleting a project permanently removes documents, files, contexts, and statistics. This action cannot be undone.',
        ru: 'Удаление проекта безвозвратно очищает документы, файлы, контексты и статистику. Действие нельзя отменить.',
        match: ['Удаление проекта безвозвратно очищает документы, файлы, контексты и статистику. Действие нельзя отменить.'],
      },
      widgetLinkHint: {
        en: 'Link appears after selecting a project.',
        ru: 'Ссылка отображается после выбора проекта',
        match: ['Ссылка отображается после выбора проекта'],
      },
      zeroPagesPlaceholder: {
        en: '0 / 0 pages',
        ru: '0 / 0 страниц',
        match: ['0 / 0 страниц'],
      },
    },
    placeholders: {
      contentPlaceholder: {
        en: 'Enter document text',
        ru: 'Введите текст документа',
        match: ['Введите текст документа'],
      },
      tokenPlaceholder: {
        en: 'Enter token',
        ru: 'Введите токен',
        match: ['Введите токен'],
      },
      shortDescriptionPlaceholder: {
        en: 'Short description',
        ru: 'Краткое описание',
        match: ['Краткое описание'],
      },
      searchPlaceholder: {
        en: 'Name or description',
        ru: 'Название или описание',
        match: ['Название или описание'],
      },
      projectNamePlaceholder: {
        en: 'Project name',
        ru: 'Название проекта',
        match: ['Название проекта'],
      },
      projectDomainPlaceholder: {
        en: 'https://example.com',
        ru: 'https://example.com',
        match: ['https://example.com'],
      },
      voiceExampleModel: {
        en: 'For example, gpt-4o-mini',
        ru: 'Например, gpt-4o-mini',
        match: ['Например, gpt-4o-mini'],
      },
      voiceExampleCatalog: {
        en: 'For example, yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest',
        ru: 'Например, yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest',
        match: ['Например, yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest'],
      },
      promptInstructionPlaceholder: {
        en: 'Describe instructions for the model',
        ru: 'Опишите инструкцию для модели',
        match: ['Опишите инструкцию для модели'],
      },
      promptProcessingPlaceholder: {
        en: 'Describe how to process documents in parts',
        ru: 'Опишите, как обрабатывать документы по частям',
        match: ['Опишите, как обрабатывать документы по частям'],
      },
      skipSettingPlaceholder: {
        en: 'Leave empty to skip setting',
        ru: 'Оставьте пустым, чтобы не задавать',
        match: ['Оставьте пустым, чтобы не задавать'],
      },
      keepUnchangedPlaceholder: {
        en: 'Leave empty to keep unchanged',
        ru: 'Оставьте пустым, чтобы не менять',
        match: ['Оставьте пустым, чтобы не менять'],
      },
      passwordPlaceholder: {
        en: 'Password',
        ru: 'Пароль',
        match: ['Пароль'],
      },
      signaturePlaceholder: {
        en: 'Regards, Example team',
        ru: 'С уважением, команда Example',
        match: ['С уважением, команда Example'],
      },
      provideInstructionPlaceholder: {
        en: 'Provide instructions for the model',
        ru: 'Укажите инструкцию для модели',
        match: ['Укажите инструкцию для модели'],
      },
      identifierPlaceholder: {
        en: 'identifier',
        ru: 'идентификатор',
        match: ['идентификатор'],
      },
    },
    titles: {
      refreshButtonTitle: {
        en: 'Refresh',
        ru: 'Обновить',
        match: ['Обновить'],
      },
      knowledgeProjectsReload: {
        en: 'Refresh project list',
        ru: 'Обновить список проектов',
        match: ['Обновить список проектов'],
      },
      logsShowTitle: {
        en: 'Show logs',
        ru: 'Показать логи',
        match: ['Показать логи'],
      },
      logsCopyTitle: {
        en: 'Copy',
        ru: 'Скопировать',
        match: ['Скопировать'],
      },
      logsHideTitle: {
        en: 'Hide',
        ru: 'Скрыть',
        match: ['Скрыть'],
      },
    },
    alt: {
      knowledgeThinkingAlt: {
        en: 'Generating description',
        ru: 'Идёт генерация описания',
        match: ['Идёт генерация описания'],
      },
    },
  };

  global.ADMIN_I18N_STATIC = STATIC_I18N;
})(window);
