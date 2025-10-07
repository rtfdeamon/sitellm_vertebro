const languageSelect = document.getElementById('adminLanguage');
const authModal = document.getElementById('adminAuthModal');
const authForm = document.getElementById('adminAuthForm');
const authUserInput = document.getElementById('adminAuthUsername');
const authPasswordInput = document.getElementById('adminAuthPassword');
const authSubmitBtn = document.getElementById('adminAuthSubmit');
const authCancelBtn = document.getElementById('adminAuthCancel');
const authError = document.getElementById('adminAuthError');
const authHint = document.getElementById('adminAuthHint');
const authMessage = document.getElementById('adminAuthMessage');
const form = document.getElementById('crawler-form');
const stopBtn = document.getElementById('stopBtn');
const crawlerProgressFill = document.getElementById('crawlerProgressFill');
const crawlerProgressStatus = document.getElementById('crawlerProgressStatus');
const crawlerProgressCounters = document.getElementById('crawlerProgressCounters');
const crawlerProgressNote = document.getElementById('crawlerProgressNote');
const crawlerLogsBtn = document.getElementById('crawlerLogsBtn');
const crawlerLogsPanel = document.getElementById('crawlerLogsPanel');
const crawlerLogsOutput = document.getElementById('crawlerLogsOutput');
const crawlerLogsRefresh = document.getElementById('crawlerLogsRefresh');
const crawlerLogsClose = document.getElementById('crawlerLogsClose');
const crawlerLogsCopy = document.getElementById('crawlerLogsCopy');
const crawlerResetBtn = document.getElementById('crawlerResetBtn');
const crawlerDedupBtn = document.getElementById('crawlerDedupBtn');
const crawlerActionStatus = document.getElementById('crawlerActionStatus');
const crawlerCollectBooks = document.getElementById('crawlerCollectBooks');
const crawlerCollectMedex = document.getElementById('crawlerCollectMedex');
const voiceTrainingCard = document.getElementById('voiceTrainingCard');
const voiceSampleInput = document.getElementById('voiceSampleInput');
const voiceSampleUploadBtn = document.getElementById('voiceSampleUpload');
const voiceUploadStatus = document.getElementById('voiceUploadStatus');
const voiceTrainingSummary = document.getElementById('voiceTrainingSummary');
const voiceSamplesContainer = document.getElementById('voiceSamplesContainer');
const voiceSamplesEmpty = document.getElementById('voiceSamplesEmpty');
const voiceTrainButton = document.getElementById('voiceTrainButton');
const voiceTrainStatus = document.getElementById('voiceTrainStatus');
const voiceRecordBtn = document.getElementById('voiceRecordBtn');
const voiceRecordStatus = document.getElementById('voiceRecordStatus');
const voiceJobsContainer = document.getElementById('voiceJobsContainer');
const kbModalBackdrop = document.getElementById('kbModal');
const kbModalClose = document.getElementById('kbModalClose');
const kbModalCancel = document.getElementById('kbModalCancel');
const kbModalSave = document.getElementById('kbModalSave');
const kbModalCompile = document.getElementById('kbModalCompile');
const kbModalTitle = document.getElementById('kbModalTitle');
const kbModalId = document.getElementById('kbModalId');
const kbModalName = document.getElementById('kbModalName');
const kbModalUrl = document.getElementById('kbModalUrl');
const kbModalDesc = document.getElementById('kbModalDescription');
const kbModalProject = document.getElementById('kbModalProject');
const kbModalContent = document.getElementById('kbModalContent');
const kbModalStatus = document.getElementById('kbModalStatus');
const backupEnabledInput = document.getElementById('backupEnabled');
const backupTimeInput = document.getElementById('backupTime');
const backupTimezoneSelect = document.getElementById('backupTimezone');
const backupFolderInput = document.getElementById('backupFolder');
const backupTokenInput = document.getElementById('backupToken');
const backupTokenSaveBtn = document.getElementById('backupTokenSave');
const backupTokenClearBtn = document.getElementById('backupTokenClear');
const backupTokenStatus = document.getElementById('backupTokenStatus');
const backupSettingsApplyBtn = document.getElementById('backupSettingsApply');
const backupStatusLine = document.getElementById('backupStatusLine');
const backupRunBtn = document.getElementById('backupRunBtn');
const backupRefreshBtn = document.getElementById('backupRefreshBtn');
const backupRestorePathInput = document.getElementById('backupRestorePath');
const backupRestoreBtn = document.getElementById('backupRestoreBtn');
const backupJobsList = document.getElementById('backupJobsList');
const backupErrorLine = document.getElementById('backupErrorLine');
const backupCard = document.getElementById('block-backup');
const projectTelegramTokenInput = document.getElementById('projectTelegramToken');
const projectTelegramAutoStart = document.getElementById('projectTelegramAutoStart');
const projectTelegramStatus = document.getElementById('projectTelegramStatus');
const projectTelegramInfo = document.getElementById('projectTelegramInfo');
const projectTelegramMessage = document.getElementById('projectTelegramMessage');
const projectTelegramSaveBtn = document.getElementById('projectTelegramSave');
const projectTelegramStartBtn = document.getElementById('projectTelegramStart');
const projectTelegramStopBtn = document.getElementById('projectTelegramStop');
const projectBitrixWebhookInput = document.getElementById('projectBitrixWebhook');
const projectBitrixEnabled = document.getElementById('projectBitrixEnabled');
const projectBitrixHint = document.getElementById('projectBitrixHint');
const projectMailEnabled = document.getElementById('projectMailEnabled');
const projectMailHint = document.getElementById('projectMailHint');
const projectMailImapHostInput = document.getElementById('projectMailImapHost');
const projectMailImapPortInput = document.getElementById('projectMailImapPort');
const projectMailImapSslInput = document.getElementById('projectMailImapSsl');
const projectMailSmtpHostInput = document.getElementById('projectMailSmtpHost');
const projectMailSmtpPortInput = document.getElementById('projectMailSmtpPort');
const projectMailSmtpTlsInput = document.getElementById('projectMailSmtpTls');
const projectMailUsernameInput = document.getElementById('projectMailUsername');
const projectMailPasswordInput = document.getElementById('projectMailPassword');
const projectMailFromInput = document.getElementById('projectMailFrom');
const projectMailSignatureInput = document.getElementById('projectMailSignature');
const projectMaxTokenInput = document.getElementById('projectMaxToken');
const projectMaxAutoStart = document.getElementById('projectMaxAutoStart');
const projectMaxStatus = document.getElementById('projectMaxStatus');
const projectMaxInfo = document.getElementById('projectMaxInfo');
const projectMaxMessage = document.getElementById('projectMaxMessage');
const projectMaxSaveBtn = document.getElementById('projectMaxSave');
const projectMaxStartBtn = document.getElementById('projectMaxStart');
const projectMaxStopBtn = document.getElementById('projectMaxStop');
const projectVkTokenInput = document.getElementById('projectVkToken');
const projectVkAutoStart = document.getElementById('projectVkAutoStart');
const projectVkStatus = document.getElementById('projectVkStatus');
const projectVkInfo = document.getElementById('projectVkInfo');
const projectVkMessage = document.getElementById('projectVkMessage');
const projectVkSaveBtn = document.getElementById('projectVkSave');
const projectVkStartBtn = document.getElementById('projectVkStart');
const projectVkStopBtn = document.getElementById('projectVkStop');
const statsCanvas = document.getElementById('statsCanvas');
const statsTooltip = document.getElementById('statsTooltip');
const statsEmpty = document.getElementById('statsEmpty');
const statsSummary = document.getElementById('statsSummary');
const statsSubtitle = document.getElementById('statsSubtitle');
const statsRefreshBtn = document.getElementById('statsRefresh');
const statsExportBtn = document.getElementById('statsExport');

const projectSelect = document.getElementById('projectSelect');                                                   
const projectStatus = document.getElementById('projectStatus');
const projectAddBtn = document.getElementById('projectAdd');
const projectRefreshBtn = document.getElementById('projectRefresh');
const projectTestBtn = document.getElementById('projectTest');
const projectPromptSaveBtn = document.getElementById('projectPromptSave');
const projectForm = document.getElementById('projectForm');
const projectWidgetUrl = document.getElementById('projectWidgetUrl');
const projectWidgetHint = document.getElementById('projectWidgetHint');
const projectWidgetLink = document.getElementById('projectWidgetLink');
const projectWidgetCopyBtn = document.getElementById('projectWidgetCopy');
const projectWidgetMessage = document.getElementById('projectWidgetMessage');
const projectDangerZone = document.getElementById('projectDangerZone');
const projectDeleteInfo = document.getElementById('projectDeleteInfo');
const crawlerProjectLabel = document.getElementById('crawlerProject');
const llmSection = document.getElementById('block-llm');
const projectNameInput = document.getElementById('projectName');
const projectDomainInput = document.getElementById('projectDomain');
const projectTitleInput = document.getElementById('projectTitle');
const projectModelInput = document.getElementById('projectModel');
const projectVoiceInput = document.getElementById('projectVoiceEnabled');
const projectVoiceHint = document.getElementById('projectVoiceHint');
const projectVoiceModelInput = document.getElementById('projectVoiceModel');
const projectPromptInput = document.getElementById('projectPrompt');
const projectPromptRoleSelect = document.getElementById('projectPromptRole');
const projectPromptAiBtn = document.getElementById('projectPromptAi');
const projectPromptAiStatus = document.getElementById('projectPromptAiStatus');
const projectEmotionsInput = document.getElementById('projectEmotions');
const projectImageCaptionsInput = document.getElementById('projectImageCaptions');
const projectImageCaptionsHint = document.getElementById('projectImageCaptionsHint');
const projectSourcesInput = document.getElementById('projectSourcesEnabled');
const projectSourcesHint = document.getElementById('projectSourcesHint');
const projectDebugInfoInput = document.getElementById('projectDebugInfo');
const projectDebugInfoHint = document.getElementById('projectDebugInfoHint');
const projectDebugInput = document.getElementById('projectDebug');
const projectDebugHint = document.getElementById('projectDebugHint');
const projectEmotionsHint = document.getElementById('projectEmotionsHint');
const projectDeleteBtn = document.getElementById('projectDelete');
const projectAdminSection = document.getElementById('projectAdminSection');
const projectAdminUsernameInput = document.getElementById('projectAdminUsername');
const projectAdminPasswordInput = document.getElementById('projectAdminPassword');
const projectAdminHint = document.getElementById('projectAdminHint');
const projectStorageText = document.getElementById('projectStorageText');
const projectStorageFiles = document.getElementById('projectStorageFiles');
const projectStorageContexts = document.getElementById('projectStorageContexts');
const projectStorageRedis = document.getElementById('projectStorageRedis');
const feedbackSection = document.getElementById('block-feedback');
const feedbackRefreshBtn = document.getElementById('feedbackRefresh');
const knowledgeServiceToggle = document.getElementById('knowledgeServiceToggle');
const knowledgeServiceApply = document.getElementById('knowledgeServiceApply');
const knowledgeServiceRefresh = document.getElementById('knowledgeServiceRefresh');
const knowledgeServiceStatus = document.getElementById('knowledgeServiceStatus');
const knowledgeServiceCard = document.querySelector('.knowledge-service-card');
const knowledgeServiceMode = document.getElementById('knowledgeServiceMode');
const knowledgeServicePrompt = document.getElementById('knowledgeServicePrompt');
const knowledgeServiceRun = document.getElementById('knowledgeServiceRun');
const knowledgeServiceEndpoints = [
  '/api/v1/knowledge/service',
  '/api/v1/admin/knowledge/service',
  '/api/v1/llm/admin/knowledge/service',
];
let activeKnowledgeServiceEndpoint = null;

const setKnowledgeServiceControlsDisabled = (disabled) => {
  if (knowledgeServiceToggle) knowledgeServiceToggle.disabled = disabled;
  if (knowledgeServiceApply) knowledgeServiceApply.disabled = disabled;
  if (knowledgeServiceRefresh) knowledgeServiceRefresh.disabled = disabled;
  if (knowledgeServiceMode) knowledgeServiceMode.disabled = disabled;
  if (knowledgeServicePrompt) knowledgeServicePrompt.disabled = disabled;
  if (knowledgeServiceRun) knowledgeServiceRun.disabled = disabled;
};

const ollamaCatalog = document.getElementById('ollamaCatalog');
const ollamaRefreshBtn = document.getElementById('ollamaRefresh');
const ollamaAvailability = document.getElementById('ollamaAvailability');
const ollamaInstalledList = document.getElementById('ollamaInstalledList');
const ollamaPopularList = document.getElementById('ollamaPopularList');
const ollamaJobsList = document.getElementById('ollamaJobsList');
const ollamaServersPanel = document.getElementById('ollamaServersPanel');
const ollamaServersList = document.getElementById('ollamaServersList');
const ollamaServersStatus = document.getElementById('ollamaServersStatus');
const ollamaServersRefreshBtn = document.getElementById('ollamaServersRefresh');
const ollamaServerForm = document.getElementById('ollamaServerForm');
const ollamaServerName = document.getElementById('ollamaServerName');
const ollamaServerUrl = document.getElementById('ollamaServerUrl');
const ollamaServerEnabled = document.getElementById('ollamaServerEnabled');
const clusterWarning = document.getElementById('clusterWarning');
const logoutButton = document.getElementById('adminLogout');
const projectModalBackdrop = document.getElementById('projectModal');
const projectModalForm = document.getElementById('projectModalForm');
const projectModalClose = document.getElementById('projectModalClose');
const projectModalCancel = document.getElementById('projectModalCancel');
const projectModalStatus = document.getElementById('projectModalStatus');
const projectModalName = document.getElementById('projectModalName');
const projectModalTitle = document.getElementById('projectModalTitle');
const projectModalDomain = document.getElementById('projectModalDomain');
const projectModalModel = document.getElementById('projectModalModel');
const projectModalPrompt = document.getElementById('projectModalPrompt');
const projectModalPromptRole = document.getElementById('projectModalPromptRole');
const projectModalPromptAiBtn = document.getElementById('projectModalPromptAi');
const projectModalPromptAiStatus = document.getElementById('projectModalPromptAiStatus');
const projectModalEmotions = document.getElementById('projectModalEmotions');
const projectModalAdminUsername = document.getElementById('projectModalAdminUsername');
const projectModalAdminPassword = document.getElementById('projectModalAdminPassword');
const projectModalWidget = document.getElementById('projectModalWidgetUrl');
const projectModalTelegram = document.getElementById('projectModalTelegram');
const projectModalTelegramAuto = document.getElementById('projectModalTelegramAuto');

const LAYOUT_ORDER_STORAGE_KEY = 'admin_layout_order_v1';

const PROMPT_AI_ROLES = [
  {
    value: 'friendly_expert',
    label: 'Дружелюбный эксперт',
    hint: 'Тёплый тон, поддержка клиента и забота о его задачах.',
  },
  {
    value: 'formal_consultant',
    label: 'Формальный консультант',
    hint: 'Деловой стиль общения, акцент на фактах и регламентах.',
  },
  {
    value: 'sales_manager',
    label: 'Активный менеджер',
    hint: 'Фокус на выгодах продукта и мягких продажах.',
  },
];

const ensurePromptRoleOptions = (select) => {
  if (!select || select.options.length) return;
  PROMPT_AI_ROLES.forEach((role) => {
    const option = document.createElement('option');
    option.value = role.value;
    option.textContent = role.label;
    if (role.hint) option.title = role.hint;
    select.appendChild(option);
  });
  if (PROMPT_AI_ROLES.length) {
    select.value = PROMPT_AI_ROLES[0].value;
  }
};

const buildTargetUrl = (raw) => {
  if (!raw) return null;
  let candidate = String(raw).trim();
  if (!candidate) return null;
  if (!/^https?:\/\//i.test(candidate)) {
    candidate = `https://${candidate}`;
  }
  try {
    const parsed = new URL(candidate);
    if (!parsed.hostname) return null;
    if (!parsed.pathname) parsed.pathname = '/';
    return parsed.toString();
  } catch (error) {
    return null;
  }
};

const initPromptAiControls = ({ textarea, domainInput, roleSelect, button, status }) => {
  if (!textarea || !domainInput || !button || !status || !roleSelect) {
    return null;
  }

  ensurePromptRoleOptions(roleSelect);
  let controller = null;
  let generating = false;

  const setStatus = (message, timeoutMs = 0) => {
    status.textContent = message || '—';
    if (timeoutMs > 0) {
      const expected = status.textContent;
      setTimeout(() => {
        if (status.textContent === expected) {
          status.textContent = '—';
        }
      }, timeoutMs);
    }
  };

  const stopGeneration = (message) => {
    if (controller) {
      controller.abort();
    }
    controller = null;
    generating = false;
    button.disabled = false;
    roleSelect.disabled = false;
    if (message) {
      setStatus(message, 3500);
    }
  };

  textarea.addEventListener('input', () => {
    if (generating) {
      stopGeneration('Остановлено: ввод пользователя');
    }
  });

  button.addEventListener('click', async () => {
    const pageUrl = buildTargetUrl(domainInput.value || projectDomainInput?.value || '');
    if (!pageUrl) {
      setStatus(t('promptAiInvalidDomain'), 4000);
      return;
    }
    const role = roleSelect.value || PROMPT_AI_ROLES[0]?.value || null;

    if (controller) {
      controller.abort();
    }
    controller = new AbortController();
    generating = true;
    button.disabled = true;
    roleSelect.disabled = true;
    setStatus(t('promptAiStart'));

    try {
      const response = await fetch('/api/v1/admin/projects/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: pageUrl, role }),
        signal: controller.signal,
      });
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const data = await response.json();
          if (data?.detail) detail = data.detail;
        } catch (error) {
          /* ignore */
        }
        throw new Error(detail || 'prompt_generation_failed');
      }
      const result = await response.json();
      const generated = typeof result?.prompt === 'string' ? result.prompt.trim() : '';
      if (!generated) {
        setStatus(t('promptAiEmpty'), 4000);
        return;
      }
      textarea.value = generated;
      setStatus(t('promptAiReady'), 2000);
    } catch (error) {
      console.error('prompt_ai_failed', error);
      if (error.name === 'AbortError') {
        setStatus('Остановлено');
      } else {
        const message = error?.message || 'prompt_generation_failed';
        setStatus(t('promptAiError', { message }), 4000);
      }
    } finally {
      generating = false;
      button.disabled = false;
      roleSelect.disabled = false;
      controller = null;
    }
  });

  return {
    abort: () => stopGeneration(),
    reset: () => setStatus('—'),
  };
};

const AUTH_CANCELLED_CODE = 'ADMIN_AUTH_CANCELLED';
const ADMIN_AUTH_HEADER_SESSION_KEY = 'admin_auth_header_v1';
const ADMIN_AUTH_USER_STORAGE_KEY = 'admin_auth_user_v1';
const ADMIN_BASE_KEY = window.location.origin.replace(/\/$/, '');
const ADMIN_PROTECTED_PREFIXES = ['/api/v1/admin/', '/api/v1/backup/'];

const {
  clearAuthHeaderForBase,
  setStoredAdminUser,
} = initAdminAuth({
  authModal,
  authForm,
  authUserInput,
  authPasswordInput,
  authSubmitBtn,
  authCancelBtn,
  authError,
  authHint,
  authMessage,
  adminBaseKey: ADMIN_BASE_KEY,
  authHeaderSessionKey: ADMIN_AUTH_HEADER_SESSION_KEY,
  authUserStorageKey: ADMIN_AUTH_USER_STORAGE_KEY,
  authCancelledCode: AUTH_CANCELLED_CODE,
  protectedPrefixes: ADMIN_PROTECTED_PREFIXES,
});

let feedbackTasksCache = [];
let feedbackTasksList = window.feedbackTasksList || document.getElementById('feedbackTasksList') || null;
window.feedbackTasksList = feedbackTasksList;
let backupState = null;
const promptAiHandlers = (window.promptAiHandlers = window.promptAiHandlers || []);
let projectsCache = {};
const startUrlInput = document.getElementById('url');
let startUrlManual = false;
if (startUrlInput) {
  startUrlInput.addEventListener('input', () => {
    startUrlManual = true;
  });
}
let voiceSamplesCache = [];
let voiceJobsCache = [];
let feedbackUnavailable = false;
let backupUnavailable = false;
let knowledgePriorityUnavailable = false;
let knowledgeQaUnavailable = false;
let knowledgeUnansweredUnavailable = false;
let voiceJobsPollTimer = null;
const VOICE_ACTIVE_STATUSES = new Set(['queued', 'preparing', 'training', 'validating']);
const VOICE_MIN_SAMPLE_COUNT = 3;
const MEDIA_RECORDER_SUPPORTED = !!(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
const voiceRecorder = {
  stream: null,
  recorder: null,
  chunks: [],
  timer: null,
  startedAt: 0,
  active: false,
  uploading: false,
  skipUpload: false,
};
const MAX_RECORDING_MS = 60_000;
let voiceJobPending = false;
let projectStatusTimer = null;
let projectStatusLocked = false;
let lastProjectCount = 0;
const llmModelDatalist = document.getElementById('llmModelOptions');
let LLM_MODEL_OPTIONS = [];
let OLLAMA_CATALOG = { available: false, installed: [], popular: [], jobs: {}, default_model: null };
let OLLAMA_INSTALLED_SET = new Set();
let ollamaPollTimer = null;
let OLLAMA_SERVERS = [];
let qaPairsCache = [];
let knowledgePriorityOrder = [];
let draggingPriorityItem = null;

const {
  t,
  applyLanguage,
  getCurrentLanguage,
} = initAdminI18n({
  languageSelect,
  authHint,
  authMessage,
  authError,
  onLanguageApplied: handleLanguageApplied,
});

applyLanguage(getCurrentLanguage());

function handleLanguageApplied() {
  if (backupState) {
    renderBackupState(backupState);
  } else if (backupJobsList) {
    backupJobsList.innerHTML = '';
    const empty = document.createElement('div');
    empty.className = 'backup-empty';
    empty.textContent = t('backupJobsEmpty');
    backupJobsList.appendChild(empty);
  }

  renderFeedbackTasks(feedbackTasksCache);
}

const STATS_DAYS = 14;
const BACKUP_TIMEZONES = [
  'UTC',
  'Europe/Kaliningrad',
  'Europe/Moscow',
  'Europe/Samara',
  'Asia/Yekaterinburg',
  'Asia/Omsk',
  'Asia/Novosibirsk',
  'Asia/Krasnoyarsk',
  'Asia/Irkutsk',
  'Asia/Yakutsk',
  'Asia/Vladivostok',
  'Asia/Sakhalin',
  'Asia/Magadan',
  'Asia/Kamchatka'
];
let backupRefreshTimer = null;
let projectStorageCache = {};
const CRAWLER_LOG_REFRESH_INTERVAL = 5000;
let lastCrawlerLogFetch = 0;
let crawlerLogsLoading = false;
resetCrawlerProgress();
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const launchMsg = document.getElementById('launchMsg');
  const payload = {
    start_url: document.getElementById('url').value,
    max_depth: Number(document.getElementById('depth').value),
    max_pages: Number(document.getElementById('pages').value),
  };
  if (crawlerCollectBooks) {
    payload.collect_books = crawlerCollectBooks.checked;
  }
  if (crawlerCollectMedex) {
    payload.collect_medex = crawlerCollectMedex.checked;
  }
  if (!currentProject) {
    launchMsg.textContent = 'Выберите проект';
    return;
  }
  payload.project = currentProject;
  const crawlDomain = projectDomainInput.value.trim();
  if (crawlDomain) {
    payload.domain = crawlDomain;
  }
  try {
    const res = await fetch('/api/v1/crawler/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    launchMsg.textContent = res.ok ? 'Запущено' : 'Не удалось запустить';
  } catch (error) {
    console.error('crawler_start_failed', error);
    launchMsg.textContent = 'Ошибка запуска краулера';
  }
});

stopBtn.addEventListener('click', async () => {
  const launchMsg = document.getElementById('launchMsg');
  try {
    const r = await fetch('/api/v1/crawler/stop', { method: 'POST' });
    launchMsg.textContent = r.ok ? 'Останавливаем…' : 'Не удалось остановить';
  } catch (error) {
    console.error('crawler_stop_failed', error);
    launchMsg.textContent = 'Ошибка остановки';
  }
});

if (crawlerLogsBtn) {
  crawlerLogsBtn.addEventListener('click', () => {
    if (!crawlerLogsPanel) return;
    if (crawlerLogsPanel.classList.contains('visible')) {
      hideCrawlerLogs();
    } else {
      showCrawlerLogs();
    }
  });
}
if (crawlerLogsClose) crawlerLogsClose.addEventListener('click', hideCrawlerLogs);
if (crawlerLogsRefresh) crawlerLogsRefresh.addEventListener('click', () => refreshCrawlerLogs(true));
if (crawlerLogsCopy) {
  crawlerLogsCopy.addEventListener('click', async () => {
    const text = crawlerLogsOutput?.textContent || '';
    if (!text.trim()) {
      setCrawlerActionStatus(t('crawlerActionNoData'), 2000);
      return;
    }
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const selection = window.getSelection();
        if (!selection) throw new Error('selection_unavailable');
        const range = document.createRange();
        range.selectNodeContents(crawlerLogsOutput);
        selection.removeAllRanges();
        selection.addRange(range);
        const legacyOk = document.execCommand('copy');
        selection.removeAllRanges();
      if (!legacyOk) throw new Error('exec_command_failed');
    }
    setCrawlerActionStatus(t('logCopySuccess'), 2000);
  } catch (error) {
    console.error('crawler_logs_copy_failed', error);
    setCrawlerActionStatus(t('logCopyError'), 3000);
  }
  });
}
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && crawlerLogsPanel?.classList.contains('visible')) {
    hideCrawlerLogs();
  }
});


async function performAdminLogout() {
  if (logoutButton) {
    logoutButton.disabled = true;
    logoutButton.textContent = t('logoutProgress');
  }
  clearAuthHeaderForBase(ADMIN_BASE_KEY);
  setStoredAdminUser('');
  const origin = window.location.origin || `${window.location.protocol}//${window.location.host}`;
  const logoutEndpoint = `${origin}/api/v1/admin/logout`;
  const nonce = Date.now().toString(36);
  const invalidAuthHeader = `Basic ${btoa(`logout:${nonce}`)}`;
  try {
    await fetch(logoutEndpoint, {
      method: 'POST',
      cache: 'no-store',
      credentials: 'include',
      headers: {
        Authorization: invalidAuthHeader,
        'Cache-Control': 'no-store, max-age=0',
        Pragma: 'no-cache',
      },
    });
  } catch (error) {
    console.warn('admin_logout_request_failed', error);
  }
  try {
    await navigator.credentials?.preventSilentAccess?.();
  } catch (error) {
    console.warn('admin_logout_credentials_failed', error);
  }
  try {
    localStorage.removeItem('admin_project');
  } catch (error) {
    console.warn('admin_logout_localstorage_failed', error);
  }
  setTimeout(() => {
    const logoutUrlWithNonce = `${window.location.protocol}//logout:${nonce}@${window.location.host}/api/v1/admin/logout?ts=${Date.now()}`;
    try {
      window.location.replace(logoutUrlWithNonce);
    } catch (error) {
      console.warn('admin_logout_replace_failed', error);
      window.location.href = `${logoutEndpoint}?ts=${Date.now()}`;
    }
  }, 120);
}

if (logoutButton) {
  logoutButton.addEventListener('click', (event) => {
    event.preventDefault();
    performAdminLogout();
  });
}

const summaryProjectCard = document.getElementById('summaryProjectCard');
const summaryProjectEl = document.getElementById('summaryProject');
const summaryProjectMeta = document.getElementById('summaryProjectMeta');
const summaryCrawlerCard = document.getElementById('summaryCrawlerCard');
const summaryCrawlerEl = document.getElementById('summaryCrawler');
const summaryCrawlerMeta = document.getElementById('summaryCrawlerMeta');
const summaryPerfEl = document.getElementById('summaryPerf');
const summaryPerfMeta = document.getElementById('summaryPerfMeta');
const summaryPromptEl = document.getElementById('summaryPrompt');
const summaryPromptDocs = document.getElementById('summaryPromptDocs');
const summaryBuildEl = document.getElementById('summaryBuild');
const summaryBuildMeta = document.getElementById('summaryBuildMeta');
const kbDedupBtn = document.getElementById('kbDeduplicate');
const kbDedupStatus = document.getElementById('kbDedupStatus');
const kbClearBtn = document.getElementById('kbClearKnowledge');
const kbClearStatus = document.getElementById('kbClearStatus');
const kbDropZone = document.getElementById('kbDropZone');
const kbDropZoneDefaultText = kbDropZone ? kbDropZone.textContent.trim() : '';
const kbNewFileInput = document.getElementById('kbNewFile');
const kbThinkingOverlay = document.getElementById('kbThinkingOverlay');
const kbThinkingCaption = document.getElementById('kbThinkingCaption');
const kbThinkingMessage = document.getElementById('kbThinkingMessage');
const kbThinkingPreview = document.getElementById('kbThinkingPreview');
const kbAutoDescription = document.getElementById('kbAutoDescription');
const kbTableText = document.getElementById('kbTableText');
const kbTableDocs = document.getElementById('kbTableDocs');
const kbTableImages = document.getElementById('kbTableImages');
const kbTableQa = document.getElementById('kbTableQa');
const kbCountText = document.getElementById('kbCountText');
const kbCountDocs = document.getElementById('kbCountDocs');
const kbCountImages = document.getElementById('kbCountImages');
const kbCountQa = document.getElementById('kbCountQa');
const kbQaStatus = document.getElementById('kbQaStatus');
const kbQaImportForm = document.getElementById('kbQaImportForm');
const kbQaFileInput = document.getElementById('kbQaFile');
const kbQaAddRowBtn = document.getElementById('kbQaAddRow');
const kbPriorityList = document.getElementById('kbPriorityList');
const kbPrioritySave = document.getElementById('kbPrioritySave');
const kbPriorityStatus = document.getElementById('kbPriorityStatus');
const kbTableUnanswered = document.getElementById('kbTableUnanswered');
const kbCountUnanswered = document.getElementById('kbCountUnanswered');
const kbUnansweredExportBtn = document.getElementById('kbUnansweredExport');
const kbUnansweredClearBtn = document.getElementById('kbUnansweredClear');
const kbUnansweredStatus = document.getElementById('kbUnansweredStatus');
const KB_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'];
const KB_TEXT_LIKE_TYPES = new Set(['application/json', 'application/xml', 'text/csv']);
const KB_STATUS_PENDING = new Set(['pending_auto_description', 'auto_description_in_progress']);
const KNOWLEDGE_SOURCES = [
  { id: 'qa', label: 'FAQ (Вопрос–ответ)' },
  { id: 'qdrant', label: 'Векторный поиск' },
  { id: 'mongo', label: 'Документы и файлы' },
];

const normalizeProjectName = (value) => (typeof value === 'string' ? value.trim().toLowerCase() : '');

const kbTables = {
  text: { body: kbTableText, counter: kbCountText, empty: 'Текстовые документы отсутствуют' },
  docs: { body: kbTableDocs, counter: kbCountDocs, empty: 'Файлы не найдены' },
  images: { body: kbTableImages, counter: kbCountImages, empty: 'Нет изображений' },
};

const getDocCategory = (doc) => {
  const contentType = String(doc.content_type || doc.contentType || '').toLowerCase();
  if (contentType.startsWith('image/')) return 'images';
  if (contentType && contentType.startsWith('text/')) return 'text';
  if (KB_TEXT_LIKE_TYPES.has(contentType)) return 'text';
  const name = String(doc.name || '').toLowerCase();
  if (KB_IMAGE_EXTENSIONS.some((ext) => name.endsWith(ext))) return 'images';
  if (contentType && !contentType.startsWith('text/')) return 'docs';
  if (doc.fileId && !contentType) return 'docs';
  return 'text';
};

const createAutoBadge = (doc) => {
  const autoPending = doc.autoDescriptionPending === true;
  const status = String(doc.status || '').toLowerCase();
  const message = doc.statusMessage || '';
  if (autoPending || KB_STATUS_PENDING.has(status)) {
    const badge = document.createElement('span');
    badge.className = 'kb-auto-badge pending';
    badge.textContent = 'AI';
    badge.title = message || 'Описание формируется';
    badge.setAttribute('aria-label', badge.title);
    return badge;
  }
  if (status === 'auto_description_failed') {
    const badge = document.createElement('span');
    badge.className = 'kb-auto-badge failed';
    badge.textContent = 'AI';
    badge.title = message || 'Автоописание не удалось';
    badge.setAttribute('aria-label', badge.title);
    return badge;
  }
  return null;
};

const createTypeBadge = (category) => {
  if (category === 'text') return null;
  const badge = document.createElement('span');
  badge.className = 'kb-type-badge';
  badge.textContent = category === 'images' ? 'Фото' : 'Файл';
  return badge;
};

const renderKnowledgeRow = (doc, category) => {
  const tr = document.createElement('tr');
  const nameTd = document.createElement('td');
  const autoBadge = createAutoBadge(doc);
  if (autoBadge) nameTd.appendChild(autoBadge);
  const typeBadge = createTypeBadge(category);
  if (typeBadge) nameTd.appendChild(typeBadge);
  nameTd.appendChild(document.createTextNode(doc.name || '–'));

  const descTd = document.createElement('td');
  descTd.textContent = doc.description || '–';

  const projectTd = document.createElement('td');
  projectTd.textContent = doc.project || doc.domain || '–';

  const linkTd = document.createElement('td');
  if (doc.fileId || doc.downloadUrl || doc.url) {
    const a = document.createElement('a');
    a.textContent = 'Скачать';
    const href = doc.downloadUrl || doc.url || `/api/v1/admin/knowledge/documents/${encodeURIComponent(doc.fileId)}`;
    a.href = href;
    a.target = '_blank';
    a.rel = 'noopener';
    if (doc.name) a.download = doc.name;
    linkTd.appendChild(a);
  } else {
    linkTd.textContent = '—';
  }

  const actionsTd = document.createElement('td');
  const editBtn = document.createElement('button');
  editBtn.type = 'button';
  editBtn.textContent = 'Редактировать';
  if (category !== 'text') {
    editBtn.textContent = 'Описание';
    editBtn.title = 'Изменить описание и метаданные';
  }
  editBtn.addEventListener('click', () => openKnowledgeModal(doc.fileId));
  actionsTd.appendChild(editBtn);

  if (doc.fileId) {
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.textContent = 'Удалить';
    deleteBtn.className = 'danger-btn';
    const docProject = (doc.project || doc.domain || currentProject || '').trim().toLowerCase();
    deleteBtn.addEventListener('click', () => deleteKnowledgeDocument(doc.fileId, docProject));
    actionsTd.appendChild(deleteBtn);
  }

  tr.append(nameTd, descTd, projectTd, linkTd, actionsTd);
  return tr;
};

const renderEmptyRow = (tbody, text) => {
  const row = document.createElement('tr');
  const cell = document.createElement('td');
  cell.colSpan = 5;
  cell.textContent = text;
  cell.className = 'muted';
  row.appendChild(cell);
  tbody.appendChild(row);
};

const normalizeKnowledgePriority = (order) => {
  const known = new Set(KNOWLEDGE_SOURCES.map((item) => item.id));
  const sanitized = Array.isArray(order)
    ? order.map((value) => String(value || '').trim()).filter((value) => known.has(value))
    : [];
  KNOWLEDGE_SOURCES.forEach((source) => {
    if (!sanitized.includes(source.id)) sanitized.push(source.id);
  });
  return sanitized;
};

const renderKnowledgePriority = (order) => {
  if (!kbPriorityList) return;
  kbPriorityList.innerHTML = '';
  knowledgePriorityOrder = normalizeKnowledgePriority(order);
  knowledgePriorityOrder.forEach((sourceId) => {
    const source = KNOWLEDGE_SOURCES.find((item) => item.id === sourceId);
    if (!source) return;
    const li = document.createElement('li');
    li.className = 'kb-priority-item';
    li.draggable = true;
    li.dataset.source = source.id;
    const label = document.createElement('span');
    label.textContent = source.label;
    li.appendChild(label);
    const handle = document.createElement('span');
    handle.className = 'kb-priority-handle';
    handle.textContent = '⋮⋮';
    li.appendChild(handle);
    kbPriorityList.appendChild(li);
  });

  kbPriorityList.querySelectorAll('.kb-priority-item').forEach((item) => {
    item.addEventListener('dragstart', (event) => {
      draggingPriorityItem = item;
      item.classList.add('dragging');
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', item.dataset.source || '');
      }
    });
    item.addEventListener('dragend', () => {
      item.classList.remove('dragging');
      draggingPriorityItem = null;
    });
  });

  if (!kbPriorityList.dataset.dragBound) {
    kbPriorityList.addEventListener('dragover', (event) => {
      if (!draggingPriorityItem) return;
      event.preventDefault();
      const target = event.target.closest('.kb-priority-item');
      if (!target || target === draggingPriorityItem) return;
      const rect = target.getBoundingClientRect();
      const after = event.clientY - rect.top > rect.height / 2;
      kbPriorityList.insertBefore(
        draggingPriorityItem,
        after ? target.nextSibling : target,
      );
    });
    kbPriorityList.dataset.dragBound = '1';
  }
};

const getKnowledgePriorityOrder = () => {
  if (!kbPriorityList) return knowledgePriorityOrder;
  const order = Array.from(kbPriorityList.querySelectorAll('.kb-priority-item'))
    .map((item) => item.dataset.source || '')
    .filter(Boolean);
  knowledgePriorityOrder = normalizeKnowledgePriority(order);
  return knowledgePriorityOrder;
};

async function loadKnowledgePriority(projectName) {
  if (!kbPriorityList || knowledgePriorityUnavailable) return;
  try {
    const params = new URLSearchParams();
    if (projectName) params.set('project', projectName);
    const query = params.toString();
    const url = query ? `/api/v1/admin/knowledge/priority?${query}` : '/api/v1/admin/knowledge/priority';
    const resp = await fetch(url);
    if (resp.status === 404) {
      knowledgePriorityUnavailable = true;
      renderKnowledgePriority(knowledgePriorityOrder);
      if (kbPriorityStatus) {
        kbPriorityStatus.textContent = 'Приоритеты недоступны';
        setTimeout(() => { kbPriorityStatus.textContent = ''; }, 4000);
      }
      return;
    }
    if (!resp.ok) throw new Error('priority_load_failed');
    const data = await resp.json();
    renderKnowledgePriority(data.order || []);
  } catch (error) {
    console.error('knowledge_priority_load_failed', error);
    renderKnowledgePriority(knowledgePriorityOrder);
    if (kbPriorityStatus) {
      kbPriorityStatus.textContent = 'Не удалось загрузить приоритеты';
    }
  }
}

async function saveKnowledgePriority() {
  if (!kbPriorityList || !kbPrioritySave || knowledgePriorityUnavailable) return;
  const order = getKnowledgePriorityOrder();
  if (kbPriorityStatus) {
    kbPriorityStatus.textContent = 'Сохраняем...';
  }
  kbPrioritySave.disabled = true;
  try {
    const payload = { order };
    const params = new URLSearchParams();
    if (currentProject) params.set('project', currentProject);
    const query = params.toString();
    const url = query ? `/api/v1/admin/knowledge/priority?${query}` : '/api/v1/admin/knowledge/priority';
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (resp.status === 404) {
      knowledgePriorityUnavailable = true;
      if (kbPriorityStatus) {
        kbPriorityStatus.textContent = 'Сохранение недоступно';
        setTimeout(() => { kbPriorityStatus.textContent = ''; }, 4000);
      }
      return;
    }
    if (!resp.ok) throw new Error(await resp.text());
    if (kbPriorityStatus) {
      kbPriorityStatus.textContent = 'Приоритеты обновлены';
    }
  } catch (error) {
    console.error('knowledge_priority_save_failed', error);
    if (kbPriorityStatus) {
      kbPriorityStatus.textContent = 'Не удалось сохранить приоритеты';
    }
  } finally {
    kbPrioritySave.disabled = false;
    setTimeout(() => {
      if (kbPriorityStatus) kbPriorityStatus.textContent = '';
    }, 4000);
  }
}
const kbNavButtons = Array.from(document.querySelectorAll('[data-kb-target]'));
const kbSections = Array.from(document.querySelectorAll('[data-kb-section]'));

const activateKnowledgeSection = (target) => {
  if (!target) return;
  kbSections.forEach((section) => {
    const matches = section.dataset.kbSection === target;
    section.classList.toggle('active', matches);
    if (matches) {
      section.removeAttribute('aria-hidden');
    } else {
      section.setAttribute('aria-hidden', 'true');
    }
  });
  kbNavButtons.forEach((button) => {
    const matches = button.dataset.kbTarget === target;
    button.classList.toggle('active', matches);
    button.setAttribute('aria-selected', matches ? 'true' : 'false');
    button.setAttribute('tabindex', matches ? '0' : '-1');
  });
};

if (kbNavButtons.length && kbSections.length) {
  const defaultTarget = (kbNavButtons.find((btn) => btn.classList.contains('active')) || kbNavButtons[0]).dataset.kbTarget;
  activateKnowledgeSection(defaultTarget);

  const focusTabByOffset = (currentIndex, delta) => {
    const total = kbNavButtons.length;
    const nextIndex = (currentIndex + delta + total) % total;
    const nextBtn = kbNavButtons[nextIndex];
    activateKnowledgeSection(nextBtn.dataset.kbTarget);
    nextBtn.focus();
  };

  kbNavButtons.forEach((button, index) => {
    button.addEventListener('click', () => {
      activateKnowledgeSection(button.dataset.kbTarget);
      button.focus();
    });
    button.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        focusTabByOffset(index, 1);
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault();
        focusTabByOffset(index, -1);
      }
    });
  });
}

const resetKnowledgePreview = () => {
  if (kbThinkingPreview) {
    kbThinkingPreview.textContent = '';
    kbThinkingPreview.classList.remove('visible');
  }
};

const showKnowledgeDescriptionPreview = (text) => {
  if (!kbThinkingPreview) return;
  const value = (text || '').trim();
  if (!value) {
    kbThinkingPreview.textContent = '';
    kbThinkingPreview.classList.remove('visible');
    return;
  }
  kbThinkingPreview.textContent = value;
  kbThinkingPreview.classList.add('visible');
};

const renderAutoDescription = (text) => {
  if (!kbAutoDescription) return;
  const value = (text || '').trim();
  if (!value) {
    kbAutoDescription.textContent = '';
    kbAutoDescription.classList.remove('visible');
    return;
  }
  kbAutoDescription.textContent = `Автоописание: ${value}`;
  kbAutoDescription.classList.add('visible');
};

const showKnowledgeThinking = (
  caption = 'Генерируем описание…',
  subtitle = 'Это может занять несколько секунд.'
) => {
  if (!kbThinkingOverlay) return;
  kbThinkingOverlay.classList.add('active');
  if (kbThinkingCaption) kbThinkingCaption.textContent = caption;
  if (kbThinkingMessage) kbThinkingMessage.textContent = subtitle;
  resetKnowledgePreview();
  renderAutoDescription('');
};

const updateKnowledgeThinking = (subtitle, caption) => {
  if (caption && kbThinkingCaption) {
    kbThinkingCaption.textContent = caption;
  }
  if (
    kbThinkingOverlay &&
    kbThinkingOverlay.classList.contains('active') &&
    kbThinkingMessage &&
    subtitle
  ) {
    kbThinkingMessage.textContent = subtitle;
  }
};

const hideKnowledgeThinking = () => {
  if (kbThinkingOverlay) kbThinkingOverlay.classList.remove('active');
  resetKnowledgePreview();
};

const summaryState = {
  project: '',
  crawler: '',
  perf: '',
  build: '',
  prompt: '',
};

const WEEK_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;

const statsGraphState = {
  data: [],
  currentPoints: [],
  startPoints: [],
  targetPoints: [],
  animationId: null,
  startTime: 0,
  duration: 520,
  hoverIndex: null,
  width: 0,
  height: 0,
  pixelRatio: window.devicePixelRatio || 1,
  lastSignature: '',
  renderedPoints: [],
};

function pulseCard(card) {
  if (!card) return;
  card.classList.remove('updated');
  void card.offsetWidth;
  card.classList.add('updated');
  setTimeout(() => card.classList.remove('updated'), 1800);
}

function updateDropZonePreview(fileList) {
  if (!kbDropZone) return;
  const files = Array.from(fileList || []).filter(Boolean);
  if (!files.length) {
    kbDropZone.textContent = kbDropZoneDefaultText || 'Перетащите файлы сюда или нажмите на поле выше';
    kbDropZone.classList.remove('has-files');
    return;
  }

  const maxPreview = 4;
  const preview = files.slice(0, maxPreview).map((file) => {
    const size = typeof file.size === 'number' ? ` (${formatBytes(file.size)})` : '';
    return `${file.name}${size}`;
  }).join(', ');
  const remaining = files.length > maxPreview ? `, +${files.length - maxPreview}` : '';
  kbDropZone.textContent = `Выбрано файлов: ${files.length}. ${preview}${remaining}`;
  kbDropZone.classList.add('has-files');
}

window.updateDropZonePreview = updateDropZonePreview;

function formatDateISO(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const formatBytesOptional = (value) => {
  const numeric = Number(value || 0);
  return numeric > 0 ? formatBytes(numeric) : '—';
};

const formatTimestamp = (value) => {
  if (value === null || value === undefined) return '—';
  let numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  if (numeric < 1e11) {
    numeric *= 1000;
  }
  const dt = new Date(numeric);
  if (Number.isNaN(dt.getTime())) return '—';
  return dt.toLocaleString();
};

const ensureBackupTimezones = () => {
  if (!backupTimezoneSelect || backupTimezoneSelect.options.length) return;
  BACKUP_TIMEZONES.forEach((tz) => {
    const option = document.createElement('option');
    option.value = tz;
    option.textContent = tz;
    backupTimezoneSelect.appendChild(option);
  });
};

const setBackupControlsDisabled = (disabled) => {
  const nodes = [
    backupEnabledInput,
    backupTimeInput,
    backupTimezoneSelect,
    backupFolderInput,
    backupTokenInput,
    backupTokenSaveBtn,
    backupTokenClearBtn,
    backupSettingsApplyBtn,
    backupRunBtn,
    backupRefreshBtn,
    backupRestorePathInput,
    backupRestoreBtn,
  ];
  nodes.forEach((node) => {
    if (node) node.disabled = disabled;
  });
};

const formatBackupTimeValue = (hour, minute) => {
  const safeHour = Math.max(0, Math.min(23, Number.isFinite(Number(hour)) ? Number(hour) : 0));
  const safeMinute = Math.max(0, Math.min(59, Number.isFinite(Number(minute)) ? Number(minute) : 0));
  return `${String(safeHour).padStart(2, '0')}:${String(safeMinute).padStart(2, '0')}`;
};

const parseBackupTime = (value) => {
  if (typeof value !== 'string') return { hour: 3, minute: 0 };
  const [hours, minutes] = value.split(':');
  const hour = Number(hours);
  const minute = Number(minutes);
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) {
    return { hour: 3, minute: 0 };
  }
  return {
    hour: Math.max(0, Math.min(23, Math.trunc(hour))),
    minute: Math.max(0, Math.min(59, Math.trunc(minute))),
  };
};

const formatBackupTimestamp = (value) => {
  if (!value) return null;
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleString();
  } catch (error) {
    return null;
  }
};

const pushBackupMessage = (key, type = 'info') => {
  if (!backupErrorLine) return;
  const message = key ? t(key) : '';
  backupErrorLine.textContent = message;
  backupErrorLine.classList.remove('bad', 'ok');
  if (!message) return;
  if (type === 'error') {
    backupErrorLine.classList.add('bad');
  } else if (type === 'success') {
    backupErrorLine.classList.add('ok');
  }
};

const scheduleBackupRefresh = (active) => {
  if (backupRefreshTimer) {
    clearTimeout(backupRefreshTimer);
    backupRefreshTimer = null;
  }
  if (active) {
    backupRefreshTimer = setTimeout(() => {
      refreshBackupStatus(false);
    }, 5000);
  }
};

const updateBackupActionButtons = () => {
  const tokenSet = Boolean(backupState?.settings?.tokenSet);
  const activeJob = Boolean(backupState?.activeJob);
  const hasRestorePath = Boolean(backupRestorePathInput?.value.trim());
  if (backupRunBtn) backupRunBtn.disabled = !adminSession.is_super || !tokenSet || activeJob;
  if (backupRefreshBtn) backupRefreshBtn.disabled = !adminSession.is_super;
  if (backupSettingsApplyBtn) backupSettingsApplyBtn.disabled = !adminSession.is_super;
  if (backupTokenSaveBtn) backupTokenSaveBtn.disabled = !adminSession.is_super;
  if (backupTokenClearBtn) backupTokenClearBtn.disabled = !adminSession.is_super;
  if (backupRestoreBtn) backupRestoreBtn.disabled = !adminSession.is_super || !tokenSet || activeJob || !hasRestorePath;
};

const renderBackupState = (data) => {
  if (!adminSession.is_super) {
    scheduleBackupRefresh(false);
    return;
  }
  ensureBackupTimezones();
  backupState = {
    settings: data?.settings || {},
    activeJob: data?.activeJob || null,
    jobs: Array.isArray(data?.jobs) ? data.jobs : [],
  };
  const settings = backupState.settings;
  if (backupEnabledInput) {
    backupEnabledInput.checked = settings.enabled === undefined ? false : Boolean(settings.enabled);
  }
  if (backupTimeInput) {
    backupTimeInput.value = formatBackupTimeValue(settings.hour ?? 3, settings.minute ?? 0);
  }
  if (backupTimezoneSelect) {
    const tzValue = settings.timezone || 'UTC';
    if (!Array.from(backupTimezoneSelect.options).some((option) => option.value === tzValue)) {
      const option = document.createElement('option');
      option.value = tzValue;
      option.textContent = tzValue;
      backupTimezoneSelect.appendChild(option);
    }
    backupTimezoneSelect.value = tzValue;
  }
  if (backupFolderInput) {
    backupFolderInput.value = settings.yaDiskFolder || '';
  }
  if (backupTokenStatus) {
    if (settings.tokenSet) {
      backupTokenStatus.textContent = t('backupTokenSaved');
      backupTokenStatus.classList.add('ok');
      backupTokenStatus.classList.remove('bad');
    } else {
      backupTokenStatus.textContent = t('backupTokenMissing');
      backupTokenStatus.classList.add('bad');
      backupTokenStatus.classList.remove('ok');
    }
  }

  const lines = [];
  const activeJob = backupState.activeJob;
  if (activeJob) {
    const statusKey = activeJob.status === 'running' ? 'backupStatusLineActive' : 'backupStatusLineQueued';
    lines.push(t(statusKey));
  } else if (!settings.enabled) {
    lines.push(t('backupStatusLineWaiting'));
  }
  const lastRunText = formatBackupTimestamp(settings.lastRunAtIso || settings.lastRunAt);
  if (lastRunText) {
    lines.push(t('backupStatusLastRun', { value: lastRunText }));
  }
  const lastSuccessText = formatBackupTimestamp(settings.lastSuccessAtIso || settings.lastSuccessAt);
  if (lastSuccessText) {
    lines.push(t('backupStatusLastSuccess', { value: lastSuccessText }));
  }
  if (!lastRunText && !lastSuccessText && !activeJob) {
    lines.push(t('backupStatusNever'));
  }
  if (backupStatusLine) {
    backupStatusLine.textContent = lines.join(' • ');
  }

  if (backupJobsList) {
    backupJobsList.innerHTML = '';
    const jobs = backupState.jobs;
    if (!jobs.length) {
      const empty = document.createElement('div');
      empty.className = 'backup-empty';
      empty.textContent = t('backupJobsEmpty');
      backupJobsList.appendChild(empty);
    } else {
      jobs.forEach((job) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'backup-job';
        if (activeJob && job.id === activeJob.id) {
          wrapper.classList.add('primary');
        }
        const operationLabel = job.operation === 'restore'
          ? t('backupJobOperationRestore')
          : t('backupJobOperationBackup');
        let statusKey = 'backupJobStatusQueued';
        if (job.status === 'running') statusKey = 'backupJobStatusRunning';
        else if (job.status === 'completed') statusKey = 'backupJobStatusCompleted';
        else if (job.status === 'failed') statusKey = 'backupJobStatusFailed';

        const title = document.createElement('strong');
        title.textContent = `${operationLabel} — ${t(statusKey)}`;
        wrapper.appendChild(title);

        if (job.remotePath) {
          const remote = document.createElement('small');
          remote.textContent = job.remotePath;
          wrapper.appendChild(remote);
        }

        if (job.createdAtIso || job.createdAt) {
          const created = document.createElement('small');
          created.textContent = formatBackupTimestamp(job.createdAtIso || job.createdAt) || '';
          wrapper.appendChild(created);
        }

        if (job.error) {
          const errorRow = document.createElement('small');
          errorRow.className = 'bad';
          errorRow.textContent = job.error;
          wrapper.appendChild(errorRow);
        }

        if (job.remotePath) {
          const actions = document.createElement('div');
          actions.className = 'backup-job-actions';
          if (job.operation === 'backup' && backupRestorePathInput) {
            const useBtn = document.createElement('button');
            useBtn.type = 'button';
            useBtn.textContent = t('backupJobRestore');
            useBtn.addEventListener('click', () => {
              backupRestorePathInput.value = job.remotePath;
              updateBackupActionButtons();
              backupRestorePathInput.focus();
            });
            actions.appendChild(useBtn);
          }
          const copyBtn = document.createElement('button');
          copyBtn.type = 'button';
          copyBtn.textContent = t('backupJobCopyPath');
          copyBtn.addEventListener('click', async () => {
            try {
              if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(job.remotePath);
              } else {
                const temp = document.createElement('textarea');
                temp.value = job.remotePath;
                document.body.appendChild(temp);
                temp.select();
                document.execCommand('copy');
                document.body.removeChild(temp);
              }
              pushBackupMessage('logCopySuccess', 'success');
            } catch (error) {
              console.error('backup_copy_path_failed', error);
              pushBackupMessage('logCopyError', 'error');
            }
          });
          actions.appendChild(copyBtn);
          wrapper.appendChild(actions);
        }

        backupJobsList.appendChild(wrapper);
      });
    }
  }

  updateBackupActionButtons();
  scheduleBackupRefresh(Boolean(activeJob));
};

const refreshBackupStatus = async (clearMessage = false) => {
  if (backupUnavailable || !adminSession.is_super) {
    scheduleBackupRefresh(false);
    return;
  }
  ensureBackupTimezones();
  if (backupRefreshTimer) {
    clearTimeout(backupRefreshTimer);
    backupRefreshTimer = null;
  }
  try {
    const resp = await fetch('/api/v1/backup/status?limit=6');
    if (resp.status === 401 || resp.status === 404) {
      backupUnavailable = true;
      setBackupControlsDisabled(true);
      if (backupCard) backupCard.style.display = 'none';
      scheduleBackupRefresh(false);
      return;
    }
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();
    renderBackupState(data);
    if (clearMessage) pushBackupMessage('', 'info');
  } catch (error) {
    if (error && error.code === AUTH_CANCELLED_CODE) {
      backupUnavailable = true;
      setBackupControlsDisabled(true);
      if (backupCard) backupCard.style.display = 'none';
      scheduleBackupRefresh(false);
      return;
    }
    console.error('backup_status_failed', error);
    pushBackupMessage('backupJobsFetchError', 'error');
  }
};

const handleBackupSettingsSave = async ({ tokenAction } = {}) => {
  if (!adminSession.is_super) return;
  ensureBackupTimezones();
  const { hour, minute } = parseBackupTime(backupTimeInput?.value || '03:00');
  const payload = {
    enabled: Boolean(backupEnabledInput?.checked),
    hour,
    minute,
    timezone: backupTimezoneSelect?.value || 'UTC',
    yaDiskFolder: backupFolderInput?.value?.trim() || 'sitellm-backups',
  };
  if (tokenAction === 'save') {
    const tokenValue = (backupTokenInput?.value || '').trim();
    if (!tokenValue) {
      pushBackupMessage('backupTokenRequired', 'error');
      return;
    }
    payload.token = tokenValue;
  } else if (tokenAction === 'clear') {
    payload.clearToken = true;
  }
  try {
    const resp = await fetch('/api/v1/backup/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    if (tokenAction === 'save' && backupTokenInput) {
      backupTokenInput.value = '';
    }
    pushBackupMessage('backupSaveSuccess', 'success');
    await refreshBackupStatus(false);
  } catch (error) {
    console.error('backup_settings_save_failed', error);
    pushBackupMessage('backupSaveError', 'error');
  }
};

const handleBackupRun = async () => {
  if (!adminSession.is_super || backupRunBtn?.disabled) return;
  try {
    backupRunBtn.disabled = true;
    const resp = await fetch('/api/v1/backup/run', { method: 'POST' });
    if (!resp.ok) {
      const detail = await resp.json().catch(() => null);
      throw new Error(detail?.detail || `HTTP ${resp.status}`);
    }
    pushBackupMessage('backupRunQueued', 'success');
    await refreshBackupStatus(false);
  } catch (error) {
    console.error('backup_run_failed', error);
    pushBackupMessage('backupSaveError', 'error');
  } finally {
    updateBackupActionButtons();
  }
};

const handleBackupRestore = async () => {
  if (!adminSession.is_super || backupRestoreBtn?.disabled) return;
  const remotePath = (backupRestorePathInput?.value || '').trim();
  if (!remotePath) {
    pushBackupMessage('backupRestorePathMissing', 'error');
    return;
  }
  try {
    backupRestoreBtn.disabled = true;
    const resp = await fetch('/api/v1/backup/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ remotePath }),
    });
    if (!resp.ok) {
      const detail = await resp.json().catch(() => null);
      throw new Error(detail?.detail || `HTTP ${resp.status}`);
    }
    pushBackupMessage('backupRestoreQueued', 'success');
    await refreshBackupStatus(false);
  } catch (error) {
    console.error('backup_restore_failed', error);
    pushBackupMessage('backupSaveError', 'error');
  } finally {
    updateBackupActionButtons();
  }
};

if (backupSettingsApplyBtn) {
  backupSettingsApplyBtn.addEventListener('click', () => handleBackupSettingsSave());
}
if (backupTokenSaveBtn) {
  backupTokenSaveBtn.addEventListener('click', () => handleBackupSettingsSave({ tokenAction: 'save' }));
}
if (backupTokenClearBtn) {
  backupTokenClearBtn.addEventListener('click', () => handleBackupSettingsSave({ tokenAction: 'clear' }));
}
if (backupRunBtn) {
  backupRunBtn.addEventListener('click', handleBackupRun);
}
if (backupRefreshBtn) {
  backupRefreshBtn.addEventListener('click', () => refreshBackupStatus(true));
}
if (backupRestoreBtn) {
  backupRestoreBtn.addEventListener('click', handleBackupRestore);
}
if (backupRestorePathInput) {
  backupRestorePathInput.addEventListener('input', () => updateBackupActionButtons());
}

function parseLogLineTimestamp(line) {
  if (!line) return null;
  try {
    const obj = JSON.parse(line);
    const ts = obj.timestamp || obj.ts || obj.time;
    if (typeof ts === 'string') {
      const parsed = Date.parse(ts);
      if (!Number.isNaN(parsed)) return parsed;
    }
  } catch {}
  const isoMatch = line.match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[\+\-]\d{2}:?\d{2})?/);
  if (isoMatch) {
    const parsed = Date.parse(isoMatch[0]);
    if (!Number.isNaN(parsed)) return parsed;
  }
  const dateMatch = line.match(/\d{4}-\d{2}-\d{2}/);
  if (dateMatch) {
    const parsed = Date.parse(`${dateMatch[0]}T00:00:00Z`);
    if (!Number.isNaN(parsed)) return parsed;
  }
  return null;
}

function filterRecentLines(lines) {
  const cutoff = Date.now() - WEEK_WINDOW_MS;
  if (!Array.isArray(lines)) return [];
  return lines.filter((line) => {
    const ts = parseLogLineTimestamp(line);
    return ts === null || ts >= cutoff;
  });
}

function renderKnowledgeServiceStatus(data) {
  if (!knowledgeServiceStatus) return;
  const bits = [];
  const message = data?.message || (data?.enabled ? 'Сервис включён' : 'Сервис выключен');
  if (message) bits.push(message);
  if (typeof data?.enabled === 'boolean') {
    bits.push(data.enabled ? 'Сервис: включён' : 'Сервис: выключен');
  }
  if (typeof data?.mode === 'string') {
    const normalized = data.mode === 'auto' ? 'автоматический' : data.mode === 'manual' ? 'ручной' : data.mode;
    bits.push(`Режим: ${normalized}`);
  }
  if (typeof data?.running === 'boolean') {
    bits.push(data.running ? 'Статус: активен' : 'Статус: остановлен');
  }
  if (typeof data?.last_queue === 'number') {
    bits.push(`Очередь: ${data.last_queue}`);
  }
  if (typeof data?.idle_seconds === 'number') {
    bits.push(`Простой: ${Math.max(0, Math.round(data.idle_seconds))} с`);
  }
  if (data?.last_run_ts) {
    bits.push(`Последний запуск: ${formatTimestamp(data.last_run_ts)}`);
  }
  if (data?.last_error) {
    bits.push(`Ошибка: ${data.last_error}`);
  }
  if (data?.manual_reason && data.manual_reason !== 'manual') {
    bits.push(`Причина: ${data.manual_reason}`);
  }
  if (data?.updated_at) {
    bits.push(`Обновлено: ${formatTimestamp(data.updated_at)}`);
  }
  knowledgeServiceStatus.textContent = bits.join(' • ') || '—';
}

async function callKnowledgeService(method = 'GET', payload = null, pathSuffix = '') {
  if (!knowledgeServiceToggle && method === 'GET') {
    return null;
  }

  const headers = { Accept: 'application/json' };
  let body;
  if (method !== 'GET' && payload !== null) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(payload);
  }

  const tried = new Set();
  const order = [];
  if (activeKnowledgeServiceEndpoint) {
    order.push(activeKnowledgeServiceEndpoint);
    tried.add(activeKnowledgeServiceEndpoint);
  }
  for (const endpoint of knowledgeServiceEndpoints) {
    if (!tried.has(endpoint)) {
      order.push(endpoint);
      tried.add(endpoint);
    }
  }

  let lastError = null;
  for (const endpoint of order) {
    const target = `${endpoint}${pathSuffix}`;
    try {
      const resp = await fetch(target, {
        method,
        headers,
        body,
        credentials: 'same-origin',
      });
      if (resp.status === 404) {
        const err = new Error('not_found');
        err.status = 404;
        lastError = err;
        continue;
      }
      if (!resp.ok) {
        const err = new Error(`HTTP ${resp.status}`);
        err.response = resp;
        throw err;
      }
      let data = null;
      if (method === 'GET') {
        data = await resp.json();
      } else if (resp.headers.get('Content-Type')?.includes('application/json')) {
        data = await resp.json();
      }
      activeKnowledgeServiceEndpoint = endpoint;
      return data;
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error('knowledge service unavailable');
}

async function fetchKnowledgeServiceStatus(triggerPulse = false) {
  if (!knowledgeServiceToggle) return;
  if (!adminSession.is_super) {
    knowledgeServiceStatus.textContent = t('knowledgeServiceUnavailable');
    setKnowledgeServiceControlsDisabled(true);
    return;
  }
  knowledgeServiceStatus.textContent = t('knowledgeServiceLoading');
  setKnowledgeServiceControlsDisabled(true);
  try {
    const data = await callKnowledgeService('GET');
    if (data) {
      knowledgeServiceToggle.checked = !!data.enabled;
      if (knowledgeServiceMode) {
        const modeValue = data.mode === 'auto' || data.mode === 'manual' ? data.mode : 'manual';
        knowledgeServiceMode.value = modeValue;
      }
      if (knowledgeServicePrompt) {
        knowledgeServicePrompt.value = typeof data.processing_prompt === 'string' ? data.processing_prompt : '';
      }
      renderKnowledgeServiceStatus(data);
      if (triggerPulse && knowledgeServiceCard) {
        pulseCard(knowledgeServiceCard);
      }
    } else {
      knowledgeServiceStatus.textContent = t('knowledgeServiceNoData');
    }
  } catch (error) {
    console.error('knowledge_service_status_failed', error);
    if (error?.message === 'not_found') {
      knowledgeServiceStatus.textContent = t('knowledgeServiceUpgrade');
    } else {
      knowledgeServiceStatus.textContent = t('knowledgeServiceFetchError');
    }
  } finally {
    setKnowledgeServiceControlsDisabled(false);
  }
}

async function saveKnowledgeServiceState() {
  if (!knowledgeServiceToggle) return;
  if (!adminSession.is_super) return;
  knowledgeServiceStatus.textContent = t('knowledgeServiceSaving');
  setKnowledgeServiceControlsDisabled(true);
  try {
    const payload = {
      enabled: knowledgeServiceToggle.checked,
    };
    if (knowledgeServiceMode) {
      payload.mode = knowledgeServiceMode.value;
    }
    if (knowledgeServicePrompt) {
      payload.processing_prompt = knowledgeServicePrompt.value;
    }
    await callKnowledgeService('POST', payload);
    knowledgeServiceStatus.textContent = t('knowledgeServiceSaved');
    await fetchKnowledgeServiceStatus(true);
  } catch (error) {
    console.error('knowledge_service_save_failed', error);
    if (error?.message === 'not_found') {
      knowledgeServiceStatus.textContent = t('knowledgeServiceUpgrade');
    } else {
      knowledgeServiceStatus.textContent = t('knowledgeServiceSaveError');
    }
  } finally {
    setKnowledgeServiceControlsDisabled(false);
  }
}

async function runKnowledgeService() {
  if (!knowledgeServiceRun) return;
  if (!adminSession.is_super) return;
  knowledgeServiceStatus.textContent = 'Запускаем обработку…';
  setKnowledgeServiceControlsDisabled(true);
  try {
    const payload = { reason: 'manual_button' };
    const result = await callKnowledgeService('POST', payload, '/run');
    if (result?.error) {
      knowledgeServiceStatus.textContent = 'Обработка завершена с ошибкой';
    } else {
      knowledgeServiceStatus.textContent = 'Обработка завершена';
    }
    await fetchKnowledgeServiceStatus(true);
  } catch (error) {
    console.error('knowledge_service_run_failed', error);
    if (error?.message === 'not_found') {
      knowledgeServiceStatus.textContent = t('knowledgeServiceUpgrade');
    } else {
      knowledgeServiceStatus.textContent = 'Ошибка запуска обработки';
    }
  } finally {
    setKnowledgeServiceControlsDisabled(false);
  }
}

function initLayoutReordering() {
  const layout = document.querySelector('.dashboard-grid');
  const toggleButton = document.getElementById('toggleLayoutOrdering');
  if (!layout || !toggleButton) return;

  const getSections = () => Array.from(layout.querySelectorAll(':scope > section[data-block-id]'));

  const saveOrder = () => {
    const order = getSections()
      .map((section) => section.dataset.blockId || '')
      .filter(Boolean);
    try {
      localStorage.setItem(LAYOUT_ORDER_STORAGE_KEY, JSON.stringify(order));
    } catch (error) {
      console.warn('layout_order_save_failed', error);
    }
  };

  const restoreOrder = () => {
    const raw = localStorage.getItem(LAYOUT_ORDER_STORAGE_KEY);
    if (!raw) return;
    try {
      const stored = JSON.parse(raw);
      if (!Array.isArray(stored) || !stored.length) return;
      const sections = getSections();
      const desiredOrder = sections.slice().sort((a, b) => {
        const aIndex = stored.indexOf(a.dataset.blockId || '');
        const bIndex = stored.indexOf(b.dataset.blockId || '');
        const fallbackA = sections.indexOf(a);
        const fallbackB = sections.indexOf(b);
        const safeA = aIndex === -1 ? stored.length + fallbackA : aIndex;
        const safeB = bIndex === -1 ? stored.length + fallbackB : bIndex;
        return safeA - safeB;
      });
      const currentSections = sections.slice();
      desiredOrder.forEach((section, index) => {
        const target = currentSections[index];
        if (!target || section === target) {
          return;
        }
        layout.insertBefore(section, target);
        const currentIndex = currentSections.indexOf(section);
        currentSections.splice(currentIndex, 1);
        currentSections.splice(index, 0, section);
      });
    } catch (error) {
      console.warn('layout_order_restore_failed', error);
    }
  };

  restoreOrder();

  const clearDropHighlights = () => {
    layout.querySelectorAll('.reorder-drop-target').forEach((el) => el.classList.remove('reorder-drop-target'));
  };

  const getDragAfterElement = (container, y) => {
    const draggableElements = [...container.querySelectorAll(':scope > section[data-block-id]:not(.dragging)')];
    let closest = { offset: Number.NEGATIVE_INFINITY, element: null };
    draggableElements.forEach((child) => {
      const rect = child.getBoundingClientRect();
      const offset = y - rect.top - rect.height / 2;
      if (offset < 0 && offset > closest.offset) {
        closest = { offset, element: child };
      }
    });
    return closest.element;
  };

  let isReorderMode = false;
  let draggingSection = null;

  const handleDragStart = (event) => {
    if (!isReorderMode) return;
    draggingSection = event.currentTarget;
    draggingSection.classList.add('dragging');
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', draggingSection.dataset.blockId || '');
    }
  };

  const handleDragEnd = (event) => {
    if (!isReorderMode) return;
    event.currentTarget.classList.remove('dragging');
    draggingSection = null;
    clearDropHighlights();
    saveOrder();
  };

  const handleDragOver = (event) => {
    if (!isReorderMode || !draggingSection) return;
    event.preventDefault();
    const afterElement = getDragAfterElement(layout, event.clientY);
    if (afterElement === draggingSection) return;
    if (afterElement == null) {
      layout.appendChild(draggingSection);
    } else {
      layout.insertBefore(draggingSection, afterElement);
    }
    clearDropHighlights();
    if (afterElement) {
      afterElement.classList.add('reorder-drop-target');
    }
  };

  layout.addEventListener('dragover', handleDragOver);
  layout.addEventListener('drop', (event) => {
    if (!isReorderMode) return;
    event.preventDefault();
    clearDropHighlights();
  });

  getSections().forEach((section) => {
    section.draggable = false;
    section.addEventListener('dragstart', handleDragStart);
    section.addEventListener('dragend', handleDragEnd);
  });

  const applyMode = (enabled) => {
    isReorderMode = enabled;
    document.body.classList.toggle('reorder-mode', enabled);
    toggleButton.textContent = enabled ? t('buttonReorderDone') : t('buttonReorder');
    toggleButton.setAttribute('aria-pressed', enabled ? 'true' : 'false');
    if (!enabled) {
      clearDropHighlights();
      if (draggingSection) {
        draggingSection.classList.remove('dragging');
        draggingSection = null;
      }
      saveOrder();
    }
    getSections().forEach((section) => {
      section.draggable = enabled;
    });
  };

  toggleButton.addEventListener('click', () => {
    applyMode(!isReorderMode);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isReorderMode) {
      applyMode(false);
    }
  });
}

function ensureStatsCanvas() {
  if (!statsCanvas) return null;
  const rect = statsCanvas.getBoundingClientRect();
  const width = rect.width || statsCanvas.parentElement?.clientWidth || 400;
  const height = rect.height || statsCanvas.parentElement?.clientHeight || 200;
  const dpr = window.devicePixelRatio || 1;
  const scaledWidth = Math.round(width * dpr);
  const scaledHeight = Math.round(height * dpr);
  if (statsCanvas.width !== scaledWidth || statsCanvas.height !== scaledHeight) {
    statsCanvas.width = scaledWidth;
    statsCanvas.height = scaledHeight;
  }
  statsGraphState.width = width;
  statsGraphState.height = height;
  statsGraphState.pixelRatio = dpr;
  return { width, height, dpr };
}

function buildStatsPoints(stats) {
  if (!stats || !stats.length) return [];
  const dims = ensureStatsCanvas();
  if (!dims) return [];
  const { width, height } = dims;
  const paddingX = 28;
  const paddingY = 24;
  const innerWidth = Math.max(width - paddingX * 2, 10);
  const innerHeight = Math.max(height - paddingY * 2, 10);
  const maxValue = Math.max(...stats.map((item) => item.count || 0), 1);
  const step = stats.length > 1 ? innerWidth / (stats.length - 1) : 0;
  return stats.map((item, idx) => ({
    x: paddingX + step * idx,
    y: height - paddingY - ((item.count || 0) / maxValue) * innerHeight,
    value: item.count || 0,
    date: item.date,
  }));
}

function drawStatsGraph(points) {
  if (!statsCanvas) return;
  const dims = ensureStatsCanvas();
  if (!dims) return;
  const { width, height, dpr } = dims;
  const ctx = statsCanvas.getContext('2d');
  const paddingX = 28;
  const paddingY = 24;
  const baseline = height - paddingY;

  ctx.save();
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  ctx.strokeStyle = 'rgba(148, 163, 184, 0.12)';
  ctx.lineWidth = 1;
  ctx.setLineDash([6, 6]);
  const gridSteps = 4;
  for (let i = 0; i <= gridSteps; i++) {
    const y = paddingY + ((baseline - paddingY) / gridSteps) * i;
    ctx.beginPath();
    ctx.moveTo(paddingX, y);
    ctx.lineTo(width - paddingX, y);
    ctx.stroke();
  }
  ctx.setLineDash([]);

  if (points.length) {
    ctx.beginPath();
    ctx.moveTo(points[0].x, baseline);
    points.forEach((pt) => ctx.lineTo(pt.x, pt.y));
    ctx.lineTo(points[points.length - 1].x, baseline);
    ctx.closePath();
    const gradient = ctx.createLinearGradient(0, paddingY, 0, baseline);
    gradient.addColorStop(0, 'rgba(96, 165, 250, 0.32)');
    gradient.addColorStop(1, 'rgba(96, 165, 250, 0.04)');
    ctx.fillStyle = gradient;
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i += 1) {
      ctx.lineTo(points[i].x, points[i].y);
    }
    ctx.strokeStyle = 'rgba(96, 165, 250, 0.9)';
    ctx.lineWidth = 2;
    ctx.stroke();

    points.forEach((pt, idx) => {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, idx === statsGraphState.hoverIndex ? 4.6 : 3.2, 0, Math.PI * 2);
      ctx.fillStyle = idx === statsGraphState.hoverIndex ? '#ffffff' : 'rgba(96, 165, 250, 0.86)';
      ctx.fill();
    });

    const highlightIndex = statsGraphState.hoverIndex ?? points.length - 1;
    if (points[highlightIndex]) {
      const pt = points[highlightIndex];
      ctx.beginPath();
      ctx.moveTo(pt.x, paddingY - 8);
      ctx.lineTo(pt.x, baseline);
      ctx.strokeStyle = 'rgba(96, 165, 250, 0.28)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }

  ctx.restore();
  statsGraphState.renderedPoints = points;
}

function animateStatsGraphTo(points, animate = true) {
  if (!animate) {
    statsGraphState.currentPoints = points;
    drawStatsGraph(points);
    return;
  }
  const previous = statsGraphState.currentPoints;
  if (!previous.length || previous.length !== points.length) {
    statsGraphState.currentPoints = points;
    drawStatsGraph(points);
    return;
  }
  const startPoints = previous.map((pt) => ({ ...pt }));
  const targetPoints = points.map((pt) => ({ ...pt }));
  const startTime = performance.now();
  const duration = statsGraphState.duration;

  if (statsGraphState.animationId) cancelAnimationFrame(statsGraphState.animationId);

  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const blended = targetPoints.map((target, idx) => {
      const origin = startPoints[idx] || target;
      return {
        x: origin.x + (target.x - origin.x) * eased,
        y: origin.y + (target.y - origin.y) * eased,
        value: target.value,
        date: target.date,
      };
    });
    statsGraphState.currentPoints = blended;
    drawStatsGraph(blended);
    if (progress < 1) {
      statsGraphState.animationId = requestAnimationFrame(step);
    }
  }

  statsGraphState.animationId = requestAnimationFrame(step);
}

function handleStatsHover(event) {
  if (!statsCanvas || !statsGraphState.renderedPoints?.length) return;
  const rect = statsCanvas.getBoundingClientRect();
  const clientX = event.touches?.[0]?.clientX ?? event.clientX;
  const x = clientX - rect.left;
  let closest = 0;
  let minDist = Number.POSITIVE_INFINITY;
  statsGraphState.renderedPoints.forEach((pt, idx) => {
    const dist = Math.abs(pt.x - x);
    if (dist < minDist) {
      minDist = dist;
      closest = idx;
    }
  });
  statsGraphState.hoverIndex = closest;
  drawStatsGraph(statsGraphState.currentPoints.length ? statsGraphState.currentPoints : statsGraphState.renderedPoints);
  if (statsTooltip && statsGraphState.data[closest]) {
    const dataPoint = statsGraphState.data[closest];
    const point = statsGraphState.renderedPoints[closest];
    statsTooltip.textContent = `${dataPoint.date}: ${dataPoint.count}`;
    statsTooltip.style.left = `${point.x}px`;
    const clampedY = Math.max(point.y, 32);
    statsTooltip.style.top = `${clampedY}px`;
    statsTooltip.classList.add('show');
  }
}

function clearStatsHover() {
  statsGraphState.hoverIndex = null;
  drawStatsGraph(statsGraphState.currentPoints);
  if (statsTooltip) statsTooltip.classList.remove('show');
}

function renderStatsChart(stats, { animate = true } = {}) {
  if (!statsCanvas) return;
  statsGraphState.hoverIndex = null;
  if (statsTooltip) statsTooltip.classList.remove('show');

  const hasData = Array.isArray(stats) && stats.length > 0;
  if (statsEmpty) statsEmpty.style.display = hasData ? 'none' : 'grid';

  if (!hasData) {
    statsGraphState.data = [];
    statsGraphState.currentPoints = [];
    drawStatsGraph([]);
    if (statsSummary) {
      statsSummary.dataset.lastText = 'Нет данных';
      statsSummary.textContent = 'Нет данных';
    }
    if (statsSubtitle) {
      statsSubtitle.textContent = `Последние ${STATS_DAYS} дней`;
    }
    return;
  }

  statsGraphState.data = stats;
  const signature = stats.map((item) => `${item.date}:${item.count || 0}`).join('|');
  const shouldAnimate = animate && statsGraphState.lastSignature && statsGraphState.lastSignature !== signature;
  statsGraphState.lastSignature = signature;

  const points = buildStatsPoints(stats);
  statsGraphState.currentPoints = statsGraphState.currentPoints.length ? statsGraphState.currentPoints : points;
  animateStatsGraphTo(points, shouldAnimate);

  const total = stats.reduce((sum, item) => sum + (item.count || 0), 0);
  const average = total && stats.length ? (total / stats.length).toFixed(1) : null;
  if (statsSummary) {
    const text = total ? `Всего ${total} запросов${average ? ` · в день ${average}` : ''}` : 'Нет данных';
    statsSummary.dataset.lastText = text;
    statsSummary.textContent = text;
  }
  if (statsSubtitle) {
    const first = stats[0]?.date;
    const last = stats[stats.length - 1]?.date;
    statsSubtitle.textContent = first && last && stats.length > 1
      ? `${first} — ${last}`
      : (first || `Последние ${STATS_DAYS} дней`);
  }
}

if (statsCanvas) {
  statsCanvas.addEventListener('mousemove', handleStatsHover);
  statsCanvas.addEventListener('mouseleave', clearStatsHover);
  statsCanvas.addEventListener('touchstart', handleStatsHover, { passive: true });
  statsCanvas.addEventListener('touchmove', handleStatsHover, { passive: true });
  statsCanvas.addEventListener('touchend', clearStatsHover);
}

window.addEventListener('resize', () => {
  if (!statsCanvas || !statsGraphState.data.length) return;
  const points = buildStatsPoints(statsGraphState.data);
  statsGraphState.currentPoints = points;
  drawStatsGraph(points);
});

async function loadRequestStats() {
  if (!statsCanvas) return;
  const previousSummary = statsSummary ? (statsSummary.dataset.lastText || statsSummary.textContent) : '';
  if (statsSummary) statsSummary.textContent = 'Загружаем…';
  if (statsEmpty) statsEmpty.textContent = 'Загрузка…';
  const params = new URLSearchParams();
  if (currentProject) params.set('project', currentProject);
  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - (STATS_DAYS - 1));
  params.set('start', formatDateISO(start));
  params.set('end', formatDateISO(end));
  try {
    const resp = await fetch(`/api/v1/admin/stats/requests?${params.toString()}`);
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    if (statsEmpty) statsEmpty.textContent = 'Нет данных';
    renderStatsChart(data.stats || [], { animate: true });
  } catch (error) {
    console.error(error);
    if (statsEmpty) {
      statsEmpty.textContent = 'Ошибка загрузки';
      statsEmpty.style.display = 'grid';
    }
    drawStatsGraph([]);
    if (statsSummary) {
      statsSummary.textContent = 'Ошибка загрузки';
    }
    setTimeout(() => {
      if (statsSummary && statsSummary.textContent === 'Ошибка загрузки') {
        statsSummary.textContent = previousSummary || '—';
      }
    }, 3000);
  }
}

async function exportRequestStats() {
  if (!statsExportBtn) return;
  const params = new URLSearchParams();
  if (currentProject) params.set('project', currentProject);
  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - (STATS_DAYS - 1));
  params.set('start', formatDateISO(start));
  params.set('end', formatDateISO(end));
  const previousSummary = statsSummary ? (statsSummary.dataset.lastText || statsSummary.textContent) : '';
  try {
    if (statsSummary) statsSummary.textContent = 'Готовим CSV…';
    const resp = await fetch(`/api/v1/admin/stats/requests/export?${params.toString()}`);
    if (!resp.ok) {
      const message = await resp.text();
      throw new Error(message || `HTTP ${resp.status}`);
    }
    const blob = await resp.blob();
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = `request-stats-${currentProject || 'all'}.csv`;
    document.body.appendChild(link);
    link.click();
    requestAnimationFrame(() => {
      document.body.removeChild(link);
      URL.revokeObjectURL(href);
    });
    if (statsSummary) {
      statsSummary.textContent = 'CSV выгружен';
      setTimeout(() => {
        if (statsSummary.textContent === 'CSV выгружен') {
          statsSummary.textContent = previousSummary || '—';
        }
      }, 2600);
    }
  } catch (error) {
    console.error(error);
    if (statsSummary) {
      statsSummary.textContent = `Ошибка экспорта: ${error.message || error}`;
      setTimeout(() => {
        if (statsSummary.textContent?.startsWith('Ошибка экспорта')) {
          statsSummary.textContent = previousSummary || '—';
        }
      }, 3600);
    }
  }
}

function setSummaryProject(name, meta) {
  const label = name || '—';
  const metaText = meta || 'Нет выбранного проекта';
  const signature = `${label}::${metaText}`;
  if (summaryState.project === signature) return;
  summaryState.project = signature;
  summaryProjectEl.textContent = label;
  summaryProjectMeta.textContent = metaText;
  pulseCard(summaryProjectCard);
}

function setSummaryCrawler(main, meta) {
  const display = main || '—';
  const metaText = meta || '';
  const signature = `${display}::${metaText}`;
  if (summaryState.crawler === signature) return;
  summaryState.crawler = signature;
  summaryCrawlerEl.textContent = display;
  summaryCrawlerMeta.textContent = metaText;
  pulseCard(summaryCrawlerCard);
}

function setSummaryPerf(main, meta) {
  const display = main || '—';
  const metaText = meta || '';
  const signature = `${display}::${metaText}`;
  if (summaryState.perf === signature) return;
  summaryState.perf = signature;
  summaryPerfEl.textContent = display;
  summaryPerfMeta.textContent = metaText;
  pulseCard(summaryPerfCard);
}

function setSummaryBuild(main, meta) {
  if (!summaryBuildEl || !summaryBuildMeta) return;
  const display = main || '—';
  const metaText = meta || '';
  const signature = `${display}::${metaText}`;
  if (summaryState.build === signature) return;
  summaryState.build = signature;
  summaryBuildEl.textContent = display;
  summaryBuildMeta.textContent = metaText || '—';
  pulseCard(summaryBuildCard);
}

function setSummaryPrompt(text, docs, meta) {
  const display = text || 'История запросов появится здесь';
  const docsList = Array.isArray(docs) ? docs.join('|') : '';
  const signature = `${display}::${docsList}::${meta || ''}`;
  if (summaryState.prompt === signature) return;
  summaryState.prompt = signature;
  summaryPromptEl.textContent = display;
  summaryPromptDocs.innerHTML = '';
  if (Array.isArray(docs) && docs.length) {
    const chipsWrap = document.createElement('div');
    chipsWrap.className = 'chips';
    docs.forEach((doc) => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = doc;
      chipsWrap.appendChild(chip);
    });
    summaryPromptDocs.appendChild(chipsWrap);
  }
  if (meta) {
    const metaEl = document.createElement('div');
    metaEl.className = 'overview-meta';
    metaEl.textContent = meta;
    summaryPromptDocs.appendChild(metaEl);
  }
  pulseCard(summaryLLMCard);
}

function updateProjectSummary() {
  if (projectStatusLocked || projectStatusTimer) return;
  if (lastProjectCount > 0) {
    projectStatus.textContent = `${lastProjectCount} проект(ов)`;
  } else {
    projectStatus.textContent = 'Добавьте проект кнопкой выше';
  }
}

async function fetchProjectStorage() {
  try {
    const resp = await fetch('/api/v1/admin/projects/storage');
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    projectStorageCache = data.projects || {};
    updateProjectDeleteInfo(currentProject);
  } catch (error) {
    console.error(error);
  }
}

function setProjectStatus(message, timeoutMs) {
  if (projectStatusTimer) {
    clearTimeout(projectStatusTimer);
    projectStatusTimer = null;
  }
  projectStatusLocked = !timeoutMs;
  projectStatus.textContent = message;
  if (timeoutMs) {
    projectStatusTimer = setTimeout(() => {
      projectStatusTimer = null;
      projectStatusLocked = false;
      updateProjectSummary();
    }, timeoutMs);
  }
}

function getPreferredModelValue(currentValue = '') {
  const trimmed = (currentValue || '').trim();
  if (trimmed) return trimmed;
  const installedOption = LLM_MODEL_OPTIONS.find((option) => option.installed);
  if (installedOption) return installedOption.value;
  if (OLLAMA_CATALOG.default_model) return OLLAMA_CATALOG.default_model;
  return '';
}

function populateModelOptions(selectedValue) {
  const normalized = (selectedValue || '').trim();
  const initialValue = normalized || getPreferredModelValue('');
  const seen = new Set();
  projectModelInput.innerHTML = '';
  projectModelInput.appendChild(new Option('— выбрать модель —', '', !initialValue, !initialValue));
  LLM_MODEL_OPTIONS.forEach(({ value: optValue, label, installed }) => {
    if (!optValue || seen.has(optValue)) return;
    seen.add(optValue);
    let display = label || optValue;
    if (installed) display = `${display} · локально`;
    const option = new Option(display, optValue, false, optValue === initialValue);
    if (installed) option.dataset.installed = '1';
    projectModelInput.appendChild(option);
  });
  if (initialValue && !seen.has(initialValue)) {
    const fallbackLabel = `${initialValue} · пользовательская`;
    projectModelInput.appendChild(new Option(fallbackLabel, initialValue, true, true));
    seen.add(initialValue);
  }
  projectModelInput.appendChild(new Option('Другая…', '__custom__', false, false));
  if (!initialValue || !seen.has(initialValue)) {
    projectModelInput.value = '';
  }
  if (llmModelDatalist) {
    const dlValues = new Set();
    llmModelDatalist.innerHTML = '';
    LLM_MODEL_OPTIONS.forEach(({ value: optValue }) => {
      if (!optValue || dlValues.has(optValue)) return;
      dlValues.add(optValue);
      const option = document.createElement('option');
      option.value = optValue;
      llmModelDatalist.appendChild(option);
    });
    if (initialValue && !dlValues.has(initialValue)) {
      const option = document.createElement('option');
      option.value = initialValue;
      llmModelDatalist.appendChild(option);
    }
  }
}

function updateProjectDeleteInfo(projectKey) {
  if (!projectDeleteBtn || !projectDeleteInfo) return;
  const normalized = (projectKey || '').trim().toLowerCase();
  if (!normalized) {
    projectDeleteBtn.disabled = true;
    projectDeleteInfo.textContent = 'Выберите проект, чтобы удалить его данные.';
    if (projectDangerZone) projectDangerZone.classList.remove('show');
    return;
  }
  if (projectDangerZone && !projectDangerZone.classList.contains('show')) {
    projectDangerZone.classList.add('show');
  }
  const storage = projectStorageCache[normalized] || null;
  const infoParts = [];
  if (storage) {
    const docCount = Number(storage.document_count || 0);
    const binaryBytes = Number(storage.binary_bytes || 0);
    const ctxCount = Number(storage.context_count || 0);
    const redisKeys = Number(storage.redis_keys || 0);
    if (docCount > 0) infoParts.push(`документов: ${docCount}`);
    if (binaryBytes > 0) infoParts.push(`файлы: ${formatBytesOptional(binaryBytes)}`);
    if (ctxCount > 0) infoParts.push(`контекстов: ${ctxCount}`);
    if (redisKeys > 0) infoParts.push(`Redis ключей: ${redisKeys}`);
  }
  projectDeleteInfo.textContent = infoParts.length
    ? `Будет удалено → ${infoParts.join(' · ')}`
    : 'Данные проекта не найдены. Удаление очистит только настройки.';
  projectDeleteBtn.disabled = false;
}

populateModelOptions('');
projectModelInput.addEventListener('change', () => {
  if (projectModelInput.value === '__custom__') {
    const custom = prompt('Введите идентификатор модели', '');
    if (custom && custom.trim()) {
      populateModelOptions(custom.trim());
    } else {
      populateProjectForm(currentProject);
    }
  }
});

function resetProjectModal() {
  if (modalPromptAiHandler && typeof modalPromptAiHandler.reset === 'function') {
    modalPromptAiHandler.reset();
  }
  projectModalName.value = '';
  projectModalTitle.value = '';
  projectModalDomain.value = '';
  projectModalModel.value = getPreferredModelValue(projectModalModel.value);
  projectModalPrompt.value = '';
  if (projectModalPromptRole) {
    ensurePromptRoleOptions(projectModalPromptRole);
    projectModalPromptRole.value = PROMPT_AI_ROLES[0]?.value || '';
  }
  if (projectModalPromptAiStatus) {
    projectModalPromptAiStatus.textContent = '—';
  }
  if (projectModalEmotions) projectModalEmotions.checked = true;
   if (projectModalAdminUsername) projectModalAdminUsername.value = '';
   if (projectModalAdminPassword) projectModalAdminPassword.value = '';
  projectModalStatus.textContent = '';
}

function showProjectModal() {
  resetProjectModal();
  projectModalBackdrop.classList.add('show');
  setTimeout(() => projectModalName.focus(), 50);
}

function hideProjectModal() {
  if (modalPromptAiHandler && typeof modalPromptAiHandler.abort === 'function') {
    modalPromptAiHandler.abort();
  }
  projectModalBackdrop.classList.remove('show');
}

if (projectAddBtn) {
  projectAddBtn.addEventListener('click', showProjectModal);
}
projectRefreshBtn.addEventListener('click', async () => {
  setProjectStatus('Обновляем…', 1500);
  try {
    await fetchProjects();
    await fetchProjectStorage();
    populateProjectForm(currentProject);
  } catch (error) {
    console.error('project_refresh_failed', error);
    setProjectStatus('Ошибка обновления списка проектов', 3000);
  }
});
projectModalClose.addEventListener('click', hideProjectModal);
projectModalCancel.addEventListener('click', hideProjectModal);
projectModalBackdrop.addEventListener('click', (event) => {
  if (event.target === projectModalBackdrop) hideProjectModal();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && projectModalBackdrop.classList.contains('show')) {
    hideProjectModal();
  }
});

projectModalForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const name = projectModalName.value.trim().toLowerCase();
  if (!name) {
    projectModalStatus.textContent = 'Укажите идентификатор';
    return;
  }
  const payload = {
    name,
    title: projectModalTitle.value.trim() || null,
    domain: projectModalDomain.value.trim() || null,
    llm_model: projectModalModel.value.trim() || null,
    llm_prompt: projectModalPrompt.value.trim() || null,
    llm_emotions_enabled: projectModalEmotions ? projectModalEmotions.checked : true,
  };
  if (adminSession.is_super && projectModalAdminUsername) {
    const modalAdmin = projectModalAdminUsername.value.trim();
    payload.admin_username = modalAdmin || null;
  }
  if (adminSession.is_super && projectModalAdminPassword) {
    const modalPassword = projectModalAdminPassword.value;
    if (modalPassword && modalPassword.trim()) {
      payload.admin_password = modalPassword;
    }
  }
  projectModalStatus.textContent = 'Создаём…';
  try {
    const resp = await fetch('/api/v1/admin/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const message = await resp.text().catch(() => '');
      throw new Error(message || `HTTP ${resp.status}`);
    }
    const saved = await resp.json();
    projectModalStatus.textContent = 'Создано';
    setTimeout(hideProjectModal, 300);
    currentProject = (saved.name || name).toLowerCase();
    await fetchProjects();
    await loadKnowledge();
    pollStatus();
    setProjectStatus('Проект создан', 3000);
  } catch (error) {
    console.error('Failed to create project', error);
    projectModalStatus.textContent = 'Ошибка создания проекта';
    setProjectStatus('Не удалось создать проект', 3000);
  }
});

async function loadLlmModels() {
  try {
    const resp = await fetch('/api/v1/admin/llm/models');
    if (!resp.ok) throw new Error('llm models request failed');
    const data = await resp.json();
    const models = Array.isArray(data.models) ? data.models : [];
    const normalized = models
      .map((m) => (typeof m === 'string' ? m.trim() : ''))
      .filter(Boolean);
    const installedSet = new Set(Array.from(OLLAMA_INSTALLED_SET));
    const options = [];
    normalized.forEach((value) => {
      if (!value || options.some((item) => item.value === value)) return;
      options.push({ value, label: value, installed: installedSet.has(value) });
    });
    installedSet.forEach((value) => {
      if (!value || options.some((item) => item.value === value)) return;
      options.push({ value, label: value, installed: true });
    });
    if (options.length) {
      options.sort((a, b) => {
        if (a.installed && !b.installed) return -1;
        if (!a.installed && b.installed) return 1;
        return a.value.localeCompare(b.value);
      });
    }
    if (options.length) {
      LLM_MODEL_OPTIONS = options;
    }
  } catch (error) {
    console.error('Cannot load LLM models', error);
    if (!LLM_MODEL_OPTIONS.length) {
      LLM_MODEL_OPTIONS = [
        'Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it',
        'yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest',
        'llama3.1:70b',
        'qwen2.5:14b',
      ].map((value) => ({ value, label: value, installed: OLLAMA_INSTALLED_SET.has(value) }));
    }
  }
  populateModelOptions(projectsCache[currentProject]?.llm_model || projectModelInput.value || '');
}

function renderOllamaInstalledList(items) {
  if (!ollamaInstalledList) return;
  ollamaInstalledList.innerHTML = '';
  if (!Array.isArray(items) || !items.length) {
    const li = document.createElement('li');
    li.className = 'ollama-meta';
    li.textContent = 'Нет локально установленных моделей';
    ollamaInstalledList.appendChild(li);
    return;
  }
  const frag = document.createDocumentFragment();
  items.forEach((item) => {
    const li = document.createElement('li');
    const name = document.createElement('span');
    name.textContent = item.name || '—';
    const meta = document.createElement('span');
    meta.className = 'ollama-meta';
    meta.textContent = item.size_human || '';
    li.appendChild(name);
    li.appendChild(meta);
    frag.appendChild(li);
  });
  ollamaInstalledList.appendChild(frag);
}

function renderOllamaPopularList(items, jobsMap) {
  if (!ollamaPopularList) return;
  ollamaPopularList.innerHTML = '';
  if (!Array.isArray(items) || !items.length) {
    const li = document.createElement('li');
    li.className = 'ollama-meta';
    li.textContent = 'Список популярных моделей пуст.';
    ollamaPopularList.appendChild(li);
    return;
  }
  const frag = document.createDocumentFragment();
  items.forEach((item) => {
    const name = item.name || '';
    if (!name) return;
    const li = document.createElement('li');
    const label = document.createElement('span');
    const meta = document.createElement('span');
    meta.className = 'ollama-meta';
    if (item.approx_size_human) {
      meta.textContent = item.approx_size_human;
    } else if (item.size_gb) {
      meta.textContent = `${item.size_gb} GB`;
    } else {
      meta.textContent = '';
    }
    label.textContent = name;
    li.appendChild(label);
    li.appendChild(meta);

    const job = jobsMap?.[name];
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'ollama-install-btn';
    if (item.installed) {
      btn.textContent = 'Установлена';
      btn.disabled = true;
    } else if (job && (job.status === 'running' || job.status === 'pending')) {
      const progress = typeof job.progress === 'number' ? ` · ${Math.round(job.progress)}%` : '';
      btn.textContent = job.status === 'running' ? `Установка${progress}` : 'В очереди';
      btn.disabled = true;
    } else {
      btn.textContent = 'Установить';
      btn.disabled = !OLLAMA_CATALOG.available;
      btn.addEventListener('click', () => startOllamaInstall(name));
    }
    li.appendChild(btn);
    frag.appendChild(li);
  });
  ollamaPopularList.appendChild(frag);
}

function renderOllamaJobs(jobs) {
  if (!ollamaJobsList) return false;
  ollamaJobsList.innerHTML = '';
  const entries = Object.values(jobs || {}).sort((a, b) => (b?.started_at || 0) - (a?.started_at || 0));
  if (!entries.length) {
    const span = document.createElement('span');
    span.className = 'ollama-meta';
    span.textContent = 'Нет активных задач';
    ollamaJobsList.appendChild(span);
    return false;
  }
  let hasRunning = false;
  const frag = document.createDocumentFragment();
  entries.forEach((job) => {
    const status = job?.status || 'unknown';
    const line = document.createElement('div');
    line.className = `ollama-job ${status}`;
    const modelName = job?.model || 'модель';
    let text = `${modelName} — ${status}`;
    if (status === 'running') {
      hasRunning = true;
      const progress = typeof job.progress === 'number' ? `${Math.round(job.progress)}%` : '';
      text = `${modelName} — устанавливается ${progress}`.trim();
    } else if (status === 'pending') {
      hasRunning = true;
      text = `${modelName} — ожидает установки`;
    } else if (status === 'success') {
      text = `${modelName} — установлена`;
    } else if (status === 'error') {
      text = `${modelName} — ошибка: ${job.error || 'не удалось'}`;
    }
    if (job.last_line && status === 'running') {
      text += ` (${job.last_line})`;
    }
    line.textContent = text;
    frag.appendChild(line);
  });
  ollamaJobsList.appendChild(frag);
  return hasRunning;
}

function renderOllamaServers(servers) {
  if (!ollamaServersList) return;
  OLLAMA_SERVERS = Array.isArray(servers) ? servers : [];
  ollamaServersList.innerHTML = '';
  if (!OLLAMA_SERVERS.length) {
    const li = document.createElement('li');
    li.className = 'ollama-meta';
    li.textContent = 'Нет зарегистрированных серверов';
    ollamaServersList.appendChild(li);
    if (ollamaServersStatus) ollamaServersStatus.textContent = 'Добавьте сервер Ollama';
    return;
  }
  const frag = document.createDocumentFragment();
  OLLAMA_SERVERS.forEach((server) => {
    const li = document.createElement('li');
    const row = document.createElement('div');
    row.className = 'ollama-server-row';

    const title = document.createElement('h4');
    title.textContent = server.name || 'сервер';
    row.appendChild(title);

    const base = document.createElement('div');
    base.className = 'ollama-meta';
    base.textContent = server.base_url || '—';
    row.appendChild(base);

    const meta = document.createElement('div');
    const enabled = Boolean(server.enabled);
    const healthy = server.healthy !== false;
    meta.className = 'ollama-server-meta';
    const avg = typeof server.avg_latency_ms === 'number'
      ? `${Math.round(server.avg_latency_ms)} мс`
      : '—';
    const reqs = typeof server.requests_last_hour === 'number'
      ? `${server.requests_last_hour}/ч`
      : '0/ч';
    const inflight = typeof server.inflight === 'number' ? `в работе: ${server.inflight}` : 'в работе: 0';
    const statusLabel = enabled ? 'активен' : 'выключен';
    const healthLabel = healthy ? 'связь есть' : 'нет связи';
    meta.appendChild(document.createTextNode(`Среднее: ${avg}`));
    meta.appendChild(document.createTextNode(` • ${reqs}`));
    meta.appendChild(document.createTextNode(` • ${inflight}`));
    meta.appendChild(document.createTextNode(` • ${statusLabel}`));
    meta.appendChild(document.createTextNode(` • ${healthLabel}`));
    row.appendChild(meta);

    if (server.last_error) {
      const errorLine = document.createElement('div');
      errorLine.className = 'ollama-meta';
      errorLine.style.color = '#f87171';
      errorLine.textContent = `Ошибка: ${server.last_error}`;
      row.appendChild(errorLine);
    }

    if (!healthy) {
      row.classList.add('ollama-server-offline');
    }

    const actions = document.createElement('div');
    actions.className = 'ollama-server-actions';
    const toggleLabel = document.createElement('label');
    toggleLabel.className = 'ollama-server-toggle';
    const toggleCheckbox = document.createElement('input');
    toggleCheckbox.type = 'checkbox';
    toggleCheckbox.checked = enabled;
    toggleCheckbox.addEventListener('change', async () => {
      const next = toggleCheckbox.checked;
      toggleCheckbox.disabled = true;
      try {
        await toggleOllamaServer(server.name, next);
      } catch (error) {
        console.error('toggle failed', error);
        toggleCheckbox.checked = !next;
      } finally {
        toggleCheckbox.disabled = false;
      }
    });
    toggleLabel.appendChild(toggleCheckbox);
    toggleLabel.append('Включён');
    actions.appendChild(toggleLabel);

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.textContent = 'Удалить';
    deleteBtn.addEventListener('click', () => deleteOllamaServer(server.name));
    actions.appendChild(deleteBtn);

    row.appendChild(actions);
    li.appendChild(row);
    frag.appendChild(li);
  });
  ollamaServersList.appendChild(frag);
  const anyHealthy = OLLAMA_SERVERS.some((server) => server.enabled && server.healthy !== false);
  if (ollamaServersStatus) {
    ollamaServersStatus.textContent = `Всего серверов: ${OLLAMA_SERVERS.length}`;
  }
  if (clusterWarning) {
    if (!anyHealthy) {
      clusterWarning.style.display = 'block';
    } else {
      clusterWarning.style.display = 'none';
    }
  }
}

async function refreshClusterAvailability() {
  if (!clusterWarning) return;
  try {
    const resp = await fetch('/api/v1/admin/llm/availability', { cache: 'no-store' });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(text || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    const available = Boolean(data?.available);
    clusterWarning.style.display = available ? 'none' : 'block';
  } catch (error) {
    console.error('cluster availability check failed', error);
    clusterWarning.style.display = 'block';
  }
}

async function refreshOllamaServers() {
  if (!ollamaServersPanel) return;
  if (ollamaServersStatus) {
    ollamaServersStatus.textContent = 'Загружаем…';
  }
  try {
    const resp = await fetch('/api/v1/admin/ollama/servers', { cache: 'no-store' });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    renderOllamaServers(data.servers || []);
  } catch (error) {
    console.error('Failed to load Ollama servers', error);
    if (ollamaServersStatus) {
      ollamaServersStatus.textContent = 'Не удалось загрузить список серверов';
    }
    if (clusterWarning) {
      clusterWarning.style.display = 'block';
    }
  }
}

const FEEDBACK_STATUS_OPTIONS = ['open', 'in_progress', 'done', 'dismissed'];

function feedbackStatusLabel(value) {
  const map = {
    open: 'feedbackStatusOpen',
    in_progress: 'feedbackStatusInProgress',
    done: 'feedbackStatusDone',
    dismissed: 'feedbackStatusDismissed',
  };
  return t(map[value] || value || 'feedbackStatusOpen');
}

function renderFeedbackTasks(tasks) {
  if (!feedbackTasksList) return;
  feedbackTasksCache = tasks || [];
  feedbackTasksList.innerHTML = '';
  if (!tasks || !tasks.length) {
    const empty = document.createElement('div');
    empty.className = 'muted';
    empty.textContent = t('feedbackNoItems');
    feedbackTasksList.appendChild(empty);
    return;
  }
  tasks.forEach((task) => {
    const item = document.createElement('div');
    item.className = 'feedback-item';

    const metaRow = document.createElement('div');
    metaRow.className = 'feedback-meta';
    if (task.project) {
      const badge = document.createElement('span');
      badge.className = 'feedback-status-badge';
      badge.textContent = `#${task.project}`;
      metaRow.appendChild(badge);
    }
    const statusBadge = document.createElement('span');
    statusBadge.className = 'feedback-status-badge';
    statusBadge.textContent = feedbackStatusLabel(task.status);
    metaRow.appendChild(statusBadge);
    const created = document.createElement('span');
    created.className = 'feedback-timestamp';
    const createdIso = task.created_at_iso || (task.created_at ? new Date(task.created_at * 1000).toISOString() : null);
    if (createdIso) created.textContent = new Date(createdIso).toLocaleString();
    metaRow.appendChild(created);
    item.appendChild(metaRow);

    const messageEl = document.createElement('div');
    messageEl.className = 'feedback-message';
    messageEl.textContent = task.message || '';
    item.appendChild(messageEl);

    if (task.contact || task.name || task.page) {
      const infoRow = document.createElement('div');
      infoRow.className = 'feedback-meta';
      if (task.name) infoRow.appendChild(document.createTextNode(task.name));
      if (task.contact) infoRow.appendChild(document.createTextNode(task.contact));
      if (task.page) {
        const link = document.createElement('a');
        link.href = task.page;
        link.target = '_blank';
        link.rel = 'noopener';
        link.textContent = task.page;
        infoRow.appendChild(link);
      }
      item.appendChild(infoRow);
    }

    const actionsRow = document.createElement('div');
    actionsRow.className = 'feedback-actions-row';
    const select = document.createElement('select');
    FEEDBACK_STATUS_OPTIONS.forEach((status) => {
      const option = document.createElement('option');
      option.value = status;
      option.textContent = feedbackStatusLabel(status);
      if (status === task.status) option.selected = true;
      select.appendChild(option);
    });
    select.addEventListener('change', () => {
      updateFeedbackTask(task.id, select.value);
    });
    actionsRow.appendChild(select);

    const updated = document.createElement('span');
    updated.className = 'feedback-timestamp';
    const updatedIso = task.updated_at_iso || (task.updated_at ? new Date(task.updated_at * 1000).toISOString() : null);
    if (updatedIso) updated.textContent = `${t('feedbackUpdated')}: ${new Date(updatedIso).toLocaleString()}`;
    actionsRow.appendChild(updated);

    item.appendChild(actionsRow);
    feedbackTasksList.appendChild(item);
  });
}

async function fetchFeedbackTasks() {
  if (feedbackUnavailable || !adminSession.is_super) {
    if (feedbackSection) feedbackSection.style.display = 'none';
    return;
  }
  if (feedbackSection) feedbackSection.style.display = '';
  try {
    const resp = await fetch('/api/v1/admin/feedback', { cache: 'no-store' });
    if (resp.status === 404) {
      feedbackUnavailable = true;
      if (feedbackSection) feedbackSection.style.display = 'none';
      return;
    }
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    renderFeedbackTasks(Array.isArray(data.tasks) ? data.tasks : []);
  } catch (error) {
    console.error('feedback_tasks_fetch_failed', error);
    if (feedbackTasksList) {
      feedbackTasksList.innerHTML = '';
      const fallback = document.createElement('div');
      fallback.className = 'muted';
      fallback.textContent = t('feedbackError');
      feedbackTasksList.appendChild(fallback);
    }
  }
}

async function updateFeedbackTask(id, status) {
  if (feedbackUnavailable) return;
  try {
    const resp = await fetch(`/api/v1/admin/feedback/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (resp.status === 404) {
      feedbackUnavailable = true;
      if (feedbackSection) feedbackSection.style.display = 'none';
      return;
    }
    if (!resp.ok) throw new Error(await resp.text());
    await fetchFeedbackTasks();
  } catch (error) {
    console.error('feedback_task_update_failed', error);
  }
}

async function submitOllamaServerForm(event) {
  event.preventDefault();
  if (!ollamaServerForm) return;
  const name = (ollamaServerName?.value || '').trim();
  const url = (ollamaServerUrl?.value || '').trim();
  if (!name || !url) {
    if (ollamaServersStatus) ollamaServersStatus.textContent = 'Укажите имя и адрес сервера';
    return;
  }
  const payload = {
    name,
    base_url: url,
    enabled: ollamaServerEnabled ? ollamaServerEnabled.checked : true,
  };
  try {
    if (ollamaServersStatus) ollamaServersStatus.textContent = 'Сохраняем сервер…';
    const resp = await fetch('/api/v1/admin/ollama/servers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const text = await resp.text();
      let message = text || `HTTP ${resp.status}`;
      try {
        const json = JSON.parse(text);
        if (json?.detail) message = json.detail;
      } catch (_) {}
      throw new Error(message);
    }
    ollamaServerName.value = '';
    if (ollamaServerEnabled) ollamaServerEnabled.checked = true;
    await refreshOllamaServers();
    if (ollamaServersStatus) ollamaServersStatus.textContent = 'Сервер сохранён';
  } catch (error) {
    console.error('Failed to upsert Ollama server', error);
    if (ollamaServersStatus) {
      const msg = error?.message || 'Не удалось сохранить сервер';
      ollamaServersStatus.textContent = msg;
    }
  }
}

async function toggleOllamaServer(name, enabled) {
  const server = OLLAMA_SERVERS.find((item) => item.name === name);
  if (!server) return;
  try {
    if (ollamaServersStatus) {
      ollamaServersStatus.textContent = enabled ? 'Включаем сервер…' : 'Отключаем сервер…';
    }
    const resp = await fetch('/api/v1/admin/ollama/servers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: server.name, base_url: server.base_url, enabled }),
    });
    if (!resp.ok) {
      const text = await resp.text();
      let message = text || `HTTP ${resp.status}`;
      try {
        const json = JSON.parse(text);
        if (json?.detail) message = json.detail;
      } catch (_) {}
      throw new Error(message);
    }
    await refreshOllamaServers();
    if (ollamaServersStatus) {
      ollamaServersStatus.textContent = enabled ? 'Сервер включён' : 'Сервер отключён';
    }
  } catch (error) {
    console.error('Failed to toggle Ollama server', error);
    if (ollamaServersStatus) {
      const msg = error?.message || 'Не удалось обновить статус сервера';
      ollamaServersStatus.textContent = msg;
    }
  }
}

async function deleteOllamaServer(name) {
  if (!name) return;
  if (!window.confirm(`Удалить сервер ${name}?`)) return;
  try {
    if (ollamaServersStatus) ollamaServersStatus.textContent = 'Удаляем сервер…';
    const resp = await fetch(`/api/v1/admin/ollama/servers/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
    if (!resp.ok) {
      const text = await resp.text();
      let message = text || `HTTP ${resp.status}`;
      try {
        const json = JSON.parse(text);
        if (json?.detail) message = json.detail;
      } catch (_) {}
      throw new Error(message);
    }
    await refreshOllamaServers();
    if (ollamaServersStatus) ollamaServersStatus.textContent = 'Сервер удалён';
  } catch (error) {
    console.error('Failed to delete Ollama server', error);
    if (ollamaServersStatus) {
      const msg = error?.message || 'Не удалось удалить сервер';
      ollamaServersStatus.textContent = msg;
    }
  }
}

async function refreshOllamaCatalog(force = false) {
  if (!adminSession.is_super || !ollamaCatalog) return;
  try {
    const resp = await fetch('/api/v1/admin/ollama/catalog', { cache: force ? 'no-store' : 'default' });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    OLLAMA_CATALOG = {
      available: Boolean(data.available),
      installed: Array.isArray(data.installed) ? data.installed : [],
      popular: Array.isArray(data.popular) ? data.popular : [],
      jobs: data.jobs || {},
      default_model: data.default_model || null,
    };
    OLLAMA_INSTALLED_SET = new Set(OLLAMA_CATALOG.installed.map((item) => item.name).filter(Boolean));
    if (ollamaAvailability) {
      ollamaAvailability.textContent = OLLAMA_CATALOG.available
        ? 'Ollama доступна для установки моделей'
        : 'Ollama недоступна. Проверьте установку runtime.';
    }
    renderOllamaInstalledList(OLLAMA_CATALOG.installed);
    renderOllamaPopularList(OLLAMA_CATALOG.popular, OLLAMA_CATALOG.jobs);
    const hasRunning = renderOllamaJobs(OLLAMA_CATALOG.jobs);
    await loadLlmModels();
    if (ollamaPollTimer) {
      clearTimeout(ollamaPollTimer);
      ollamaPollTimer = null;
    }
    if (hasRunning) {
      ollamaPollTimer = setTimeout(() => refreshOllamaCatalog(true), 4000);
    }
  } catch (error) {
    console.error('ollama_catalog_failed', error);
    if (ollamaAvailability) {
      ollamaAvailability.textContent = 'Не удалось загрузить каталог моделей';
    }
  }
}

async function startOllamaInstall(model) {
  if (!model || !adminSession.is_super) return;
  try {
    const resp = await fetch('/api/v1/admin/ollama/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(text || `HTTP ${resp.status}`);
    }
  } catch (error) {
    console.error('ollama_install_failed', error);
    if (ollamaJobsList) {
      const row = document.createElement('div');
      row.className = 'ollama-job error';
      row.textContent = `Не удалось запустить установку: ${error?.message || 'ошибка'}`;
      ollamaJobsList.prepend(row);
    }
  }
  await refreshOllamaCatalog(true);
}

function updateProjectInputs(){
  const projectField = document.getElementById('kbProject');
  const project = projectsCache[currentProject] || null;
  projectField.value = project ? project.name : (currentProject || '');
}

function resetCrawlerProgress() {
  if (crawlerProgressFill) crawlerProgressFill.style.width = '0%';
  if (crawlerProgressStatus) crawlerProgressStatus.textContent = 'Ожидание запуска';
  if (crawlerProgressCounters) crawlerProgressCounters.textContent = '0 / 0 страниц';
  if (crawlerProgressNote) {
    crawlerProgressNote.textContent = '';
    crawlerProgressNote.style.display = 'none';
  }
}

function setCrawlerProgressError(message = 'Не удалось получить данные о краулере') {
  if (crawlerProgressFill) crawlerProgressFill.style.width = '0%';
  if (crawlerProgressStatus) crawlerProgressStatus.textContent = 'Ошибка статуса';
  if (crawlerProgressCounters) crawlerProgressCounters.textContent = '—';
  if (crawlerProgressNote) {
    crawlerProgressNote.textContent = message;
    crawlerProgressNote.style.display = 'block';
  }
}

function updateCrawlerProgress(active, queued, done, failed, note, lastUrl) {
  if (crawlerProgressFill) {
    const total = Math.max(active + queued + done + failed, 0);
    const completed = Math.max(done, 0);
    const percent = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;
    crawlerProgressFill.style.width = `${percent}%`;
  }
  if (crawlerProgressStatus) {
    let statusText = 'Ожидание запуска';
    if (active > 0) statusText = `Сканирование (${active})`;
    else if (queued > 0) statusText = `В очереди (${queued})`;
    else if (failed > 0) statusText = 'Ошибки';
    else if (done > 0) statusText = 'Готово';
    crawlerProgressStatus.textContent = statusText;
  }
  if (crawlerProgressCounters) {
    const total = Math.max(active + queued + done + failed, 0);
    const completed = Math.max(done, 0);
    const base = total > 0 ? `${completed} / ${total} страниц` : '0 / 0 страниц';
    crawlerProgressCounters.textContent = failed > 0 ? `${base} · ошибок: ${failed}` : base;
  }
  if (crawlerProgressNote) {
    const bits = [];
    if (note) bits.push(String(note));
    if (lastUrl) bits.push(`Последний URL: ${lastUrl}`);
    crawlerProgressNote.textContent = bits.join('\n');
    crawlerProgressNote.style.display = bits.length ? 'block' : 'none';
  }
}

let crawlerActionTimer = null;
const setCrawlerActionStatus = (message = '', timeout = 3000) => {
  if (!crawlerActionStatus) return;
  if (crawlerActionTimer) {
    clearTimeout(crawlerActionTimer);
    crawlerActionTimer = null;
  }
  crawlerActionStatus.textContent = message || '';
  if (timeout > 0 && message) {
    crawlerActionTimer = setTimeout(() => {
      crawlerActionStatus.textContent = '';
      crawlerActionTimer = null;
    }, timeout);
  }
};

async function refreshCrawlerLogs(force = false) {
  if (!crawlerLogsOutput) return;
  const now = Date.now();
  if (!force && !crawlerLogsPanel?.classList.contains('visible')) return;
  if (!force && now - lastCrawlerLogFetch < CRAWLER_LOG_REFRESH_INTERVAL) return;
  if (crawlerLogsLoading) return;
  crawlerLogsLoading = true;
  crawlerLogsOutput.textContent = 'Загружаем…';
  try {
    const resp = await fetch('/api/v1/admin/logs?limit=400');
    if (!resp.ok) throw new Error('logs request failed');
    const data = await resp.json();
    const lines = Array.isArray(data.lines) ? data.lines : [];
    const filtered = lines.filter((line) => /crawler/i.test(line));
    crawlerLogsOutput.textContent = filtered.length ? filtered.join('\n') : 'Логи краулера пока пусты.';
  } catch (error) {
    console.error('crawler logs fetch failed', error);
    crawlerLogsOutput.textContent = 'Не удалось загрузить логи краулера';
  } finally {
    crawlerLogsLoading = false;
    lastCrawlerLogFetch = Date.now();
  }
}

const buildCrawlerActionUrl = (path) => {
  const base = `/api/v1/crawler${path}`;
  if (currentProject) {
    return `${base}?project=${encodeURIComponent(currentProject)}`;
  }
  return base;
};

async function performCrawlerAction(path, successMessage) {
  if (!currentProject) {
    setCrawlerActionStatus(t('crawlerSelectProject'), 2500);
    return;
  }
  setCrawlerActionStatus(t('crawlerActionProcessing'), 0);
  try {
    const resp = await fetch(buildCrawlerActionUrl(path), { method: 'POST' });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(text || `HTTP ${resp.status}`);
    }
    setCrawlerActionStatus(successMessage, 2000);
    await pollStatus();
    await refreshCrawlerLogs(true);
  } catch (error) {
    console.error('crawler_action_failed', error);
    setCrawlerActionStatus(t('crawlerActionExecuteError'), 3000);
  }
}

function showCrawlerLogs() {
  if (!crawlerLogsPanel) return;
  crawlerLogsPanel.classList.add('visible');
  refreshCrawlerLogs(true);
}

function hideCrawlerLogs() {
  if (!crawlerLogsPanel) return;
  crawlerLogsPanel.classList.remove('visible');
}
async function pollStatus() {
  if (!currentProject) {
    document.getElementById('queued').textContent = '0';
    document.getElementById('in_progress').textContent = '0';
    document.getElementById('done').textContent = '0';
    document.getElementById('failed').textContent = '0';
    document.getElementById('last_crawl').textContent = 'Last: –';
    document.getElementById('recent_urls').innerHTML = '';
    setSummaryCrawler('Нет данных', 'Выберите проект слева');
    resetCrawlerProgress();
    return;
  }
  try {
    const url = currentProject ? `/api/v1/crawler/status?project=${encodeURIComponent(currentProject)}` : '/api/v1/crawler/status';
    const resp = await fetch(url);
    if (resp.ok) {
      const data = await resp.json();
      const crawlerData = data.crawler || {};
      document.getElementById('queued').textContent = data.queued ?? 0;
      document.getElementById('in_progress').textContent = data.in_progress ?? 0;
      document.getElementById('done').textContent = data.done ?? 0;
      document.getElementById('failed').textContent = data.failed ?? 0;
      const iso = data.last_crawl_iso || '–';
      document.getElementById('last_crawl').textContent = 'Last: ' + iso;
      const list = document.getElementById('recent_urls');
      list.innerHTML = '';
      const arr = (data.crawler && data.crawler.recent_urls) || data.recent_urls || [];
      const uniqueUrls = [];
      const seenUrls = new Set();
      for (const candidate of arr) {
        const trimmed = (candidate || '').trim();
        if (!trimmed || seenUrls.has(trimmed)) continue;
        seenUrls.add(trimmed);
        uniqueUrls.push(trimmed);
      }
      for (const u of uniqueUrls) {
        const li = document.createElement('li');
        const a = document.createElement('a'); a.href = u; a.textContent = u; a.target = '_blank';
        li.appendChild(a); list.appendChild(li);
      }
      const active = Number(data.in_progress ?? 0);
      const queued = Number(data.queued ?? 0);
      const done = Number(data.done ?? 0);
      const failed = Number(data.failed ?? 0);
      const summaryMain = `${active} в работе · ${queued} в очереди`;
      const metaLines = [`Готово: ${done}`, `Ошибки: ${failed}`];
      if (data.last_url) metaLines.push(`Последний: ${data.last_url}`);
      if (iso && iso !== '–') metaLines.push(`Последний запуск: ${iso}`);
      setSummaryCrawler(summaryMain, metaLines.join('\n'));
      updateCrawlerProgress(
        active,
        queued,
        done,
        failed,
        data.notes || crawlerData.notes || '',
        data.last_url || crawlerData.last_url || ''
      );
      if (crawlerLogsPanel?.classList.contains('visible')) {
        refreshCrawlerLogs();
      }
    } else {
      setCrawlerProgressError('Не удалось получить статус краулера');
    }
  } catch (err) {
    console.error(err);
    setSummaryCrawler('Ошибка', 'Не удалось получить статус краулера');
    setCrawlerProgressError();
  }
}

async function pollHealth() {
  try {
    const r = await fetch('/health');
    if (!r.ok) return;
    const h = await r.json();
    const details = h.details || {};
    const set = (id, ok) => {
      const el = document.getElementById(id);
      const error = details[id] && details[id].error ? details[id].error : '';
      el.textContent = ok ? 'up' : 'down';
      el.className = ok ? 'ok' : 'bad';
      el.title = error;
    };
    set('mongo', !!h.mongo);
    set('redis', !!h.redis);
    set('qdrant', !!h.qdrant);
    document.getElementById('overall').textContent = h.status || 'unknown';
  } catch (error) {
    console.error(error);
  }
}

async function pollLLM() {
  try {
    const r = await fetch('/api/v1/llm/info');
    if (!r.ok) return;
    const j = await r.json();
    document.getElementById('model').textContent = j.model || '–';
    document.getElementById('backend').textContent = j.backend || '–';
    document.getElementById('device').textContent = j.device || '–';
    document.getElementById('ollamaBase').value = j.ollama_base || '';
    if (j.model) {
      document.getElementById('ollamaModel').value = j.model;
    }
  } catch (error) {
    console.error(error);
    setSummaryPerf('Ошибка', 'Не удалось получить /sysinfo');
  }
}

function formatBytes(n){ if(!n && n!==0) return '–'; const u=['B','KB','MB','GB','TB']; let i=0; while(n>=1024 && i<u.length-1){ n/=1024; i++; } return n.toFixed(1)+' '+u[i]; }
function formatPercent(v){ return (typeof v === 'number' && !Number.isNaN(v)) ? v.toFixed(1) + '%' : '–'; }
async function pollSys() {
  try {
    const r = await fetch('/sysinfo');
    if (!r.ok) return;
    const j = await r.json();
    document.getElementById('cpu').textContent = formatPercent(j.cpu_percent);
    document.getElementById('cpuSys').textContent = formatPercent(j.system_cpu_percent);
    const rss = typeof j.rss_bytes === 'number' ? formatBytes(j.rss_bytes) : '–';
    document.getElementById('rss').textContent = rss;
    const ram = (typeof j.memory_used_bytes === 'number' && typeof j.memory_total_bytes === 'number')
      ? `${formatBytes(j.memory_used_bytes)} / ${formatBytes(j.memory_total_bytes)}${typeof j.memory_percent === 'number' ? ' (' + j.memory_percent.toFixed(1) + '%)' : ''}`
      : '–';
    document.getElementById('ram').textContent = ram;
    const gpuEl = document.getElementById('gpu');
    if (Array.isArray(j.gpus) && j.gpus.length) {
      const lines = j.gpus.map((g, idx) => {
        const label = g.name || `GPU ${idx}`;
        const util = formatPercent(g.util_percent);
        let memInfo = '';
        if (typeof g.memory_used_bytes === 'number' && typeof g.memory_total_bytes === 'number') {
          memInfo = `${formatBytes(g.memory_used_bytes)} / ${formatBytes(g.memory_total_bytes)}`;
        }
        return `${label}: ${util}${memInfo ? ' · ' + memInfo : ''}`;
      });
      gpuEl.textContent = lines.join('\n');
    } else {
      gpuEl.textContent = '—';
    }
    document.getElementById('pyver').textContent = j.python || '';
    const cpuDisplay = formatPercent(j.cpu_percent);
    const sysDisplay = formatPercent(j.system_cpu_percent);
    const gpuDisplay = gpuEl.textContent || '';
    const perfLines = [
      sysDisplay && sysDisplay !== '–' ? `Система: ${sysDisplay}` : '',
      ram !== '–' ? `RAM: ${ram}` : '',
      rss !== '–' ? `RSS: ${rss}` : '',
      gpuDisplay && gpuDisplay !== '—' ? `GPU: ${gpuDisplay.split('\n')[0]}` : '',
    ].filter(Boolean);
    setSummaryPerf(cpuDisplay, perfLines.join('\n'));

    const build = j.build || {};
    const rawVersion = build.version && build.version !== 'unknown' ? String(build.version) : '';
    let buildTitle = rawVersion ? `v${rawVersion}` : '—';
    const shortRev = build.revision ? String(build.revision).slice(0, 8) : '';
    if (shortRev) {
      buildTitle = buildTitle !== '—' ? `${buildTitle} · ${shortRev}` : shortRev;
    }

    let builtAtSeconds = null;
    if (typeof build.built_at === 'number' && Number.isFinite(build.built_at)) {
      builtAtSeconds = build.built_at;
    } else if (typeof build.built_at_iso === 'string') {
      const parsedIso = Date.parse(build.built_at_iso);
      if (!Number.isNaN(parsedIso)) {
        builtAtSeconds = parsedIso / 1000;
      }
    }

    const buildMetaLines = [];
    if (builtAtSeconds !== null) {
      const formatted = formatTimestamp(builtAtSeconds);
      if (formatted && formatted !== '—') {
        buildMetaLines.push(`Собрано: ${formatted}`);
      }
    }

    if (build.components && typeof build.components === 'object') {
      const componentEntries = Object.entries(build.components).slice(0, 3);
      for (const [name, payload] of componentEntries) {
        if (!payload || typeof payload !== 'object') continue;
        const compVersion = payload.version ? `v${payload.version}` : '';
        const compRevision = payload.revision ? String(payload.revision).slice(0, 8) : '';
        const parts = [compVersion, compRevision].filter(Boolean);
        if (parts.length) {
          buildMetaLines.push(`${name}: ${parts.join(' · ')}`);
        }
      }
    }

    setSummaryBuild(buildTitle, buildMetaLines.join('\n') || '—');
  } catch {}
}

async function pollLogs(){
  const lim = Number(document.getElementById('logLimit').value || 200);
  try{
    const r = await fetch(`/api/v1/admin/logs?limit=${lim}`);
    if(!r.ok) return;
    const j = await r.json();
    const lines = filterRecentLines((j && j.lines) || []);
    const pre = document.getElementById('logs');
    pre.textContent = lines.join('\n');
    document.getElementById('logInfo').textContent = `${lines.length} lines · 7 дней`;
    // auto-scroll to bottom
    pre.scrollTop = pre.scrollHeight;
    const promptEl = document.getElementById('promptLogs');
    if (promptEl) {
      const prompts = [];
      let latestMatch = null;
      for (const line of lines) {
        if (!line.includes('llm_prompt_compiled')) continue;
        let formatted = line;
        let parsed = null;
        try {
          parsed = JSON.parse(line);
          const preview = parsed.prompt_preview || parsed.prompt_base || '';
          const project = parsed.project || parsed.mode || '';
          const knowledge = parsed.knowledge || [];
          const docs = knowledge.map((item) => item.name || item.url || item.id).filter(Boolean).join(', ');
          formatted = `[${project}] ${preview}${docs ? `\n  docs: ${docs}` : ''}`;
        } catch (err) {
          // keep raw line if parsing fails
        }
        if (parsed) {
          const projectKey = (parsed.project || parsed.mode || '').toLowerCase();
          if (!currentProject || !projectKey || projectKey === currentProject) {
            const previewText = (parsed.prompt_preview || parsed.prompt_base || '').trim();
            const clipped = previewText.length > 280 ? `${previewText.slice(0, 277)}…` : previewText || formatted;
            const knowledgeDocs = Array.isArray(parsed.knowledge) ? parsed.knowledge : [];
            const docNames = knowledgeDocs
              .map((item) => item.name || item.url || item.id)
              .filter(Boolean)
              .map(String)
              .slice(0, 6);
            const metaParts = [];
            if (parsed.prompt_length) metaParts.push(`Длина: ${parsed.prompt_length}`);
            if (parsed.session) metaParts.push(`Сессия: ${parsed.session}`);
            latestMatch = { text: clipped, docs: docNames, meta: metaParts.join(' · ') };
          }
        }
        prompts.push(formatted);
      }
      promptEl.textContent = prompts.join('\n\n');
      promptEl.scrollTop = promptEl.scrollHeight;
      if (latestMatch) {
        setSummaryPrompt(latestMatch.text, latestMatch.docs, latestMatch.meta);
      }
    }
  }catch(e){}
}

function tick(){
  pollStatus();
  pollHealth();
  pollLLM();
  pollSys();
  pollLogs();
}
tick();
setInterval(tick, 3000);

async function loadKnowledge(){
  if (kbDedupStatus) kbDedupStatus.textContent = '';
  if (!currentProject) {
    Object.values(kbTables).forEach(({ body, counter, empty }) => {
      body.innerHTML = '';
      renderEmptyRow(body, 'Выберите проект');
      if (counter) counter.textContent = '—';
    });
    document.getElementById('kbInfo').textContent = 'Выберите проект';
    return;
  }
  const limitField = document.getElementById('kbLimit');
  const qField = document.getElementById('kbSearch');
  const params = new URLSearchParams();
  const limit = Number(limitField.value || 1000);
  if (Number.isFinite(limit)) params.set('limit', Math.min(Math.max(limit, 10), 1000));
  const query = qField.value.trim();
  if (query) params.set('q', query);
  if (currentProject) {
    const projectId = currentProject.trim().toLowerCase();
    params.set('project', projectId);
  }
  if (kbPriorityList) {
    await loadKnowledgePriority(currentProject);
  }
  try {
    const resp = await fetch(`/api/v1/admin/knowledge?${params.toString()}`);
    if (!resp.ok) throw new Error('knowledge request failed');
    const data = await resp.json();
    const docs = data.documents || [];
    const grouped = { text: [], docs: [], images: [] };
    docs.forEach((doc) => {
      const category = getDocCategory(doc);
      grouped[category].push(doc);
    });

    Object.entries(kbTables).forEach(([key, cfg]) => {
      if (!cfg.body) return;
      cfg.body.innerHTML = '';
      const items = grouped[key] || [];
      if (cfg.counter) cfg.counter.textContent = items.length ? String(items.length) : '—';
      if (!items.length) {
        const emptyMessage = query ? 'Ничего не найдено' : cfg.empty;
        renderEmptyRow(cfg.body, emptyMessage);
        return;
      }
      for (const doc of items) {
        cfg.body.appendChild(renderKnowledgeRow(doc, key));
      }
    });

    const matched = data.matched ?? docs.length;
    const total = data.total ?? matched;
    const infoParts = [
      `Всего: ${docs.length} / ${matched}${total ? ` (всего ${total})` : ''}`,
      `Текст: ${grouped.text.length}`,
      `Документы: ${grouped.docs.length}`,
      `Фото: ${grouped.images.length}`,
    ];
    if (currentProject) infoParts.push(`Проект: ${currentProject}`);
    if (query) infoParts.push(`Фильтр: "${query}"`);
    document.getElementById('kbInfo').textContent = infoParts.join(' · ');
    await loadKnowledgeQa();
    await loadUnansweredQuestions();
  } catch (error) {
    document.getElementById('kbInfo').textContent = 'Ошибка загрузки базы знаний';
    console.error(error);
  }
}

function renderQaEmpty(text) {
  if (!kbTableQa) return;
  kbTableQa.innerHTML = '';
  const row = document.createElement('tr');
  const cell = document.createElement('td');
  cell.colSpan = 4;
  cell.textContent = text;
  cell.className = 'muted';
  row.appendChild(cell);
  kbTableQa.appendChild(row);
}

function renderQaTable(items) {
  if (!kbTableQa) return;
  kbTableQa.innerHTML = '';
  if (!Array.isArray(items) || !items.length) {
    renderQaEmpty(currentProject ? 'Добавьте вопросы вручную или импортируйте файл' : 'Выберите проект');
    return;
  }
  items.forEach((item, index) => {
    const tr = document.createElement('tr');
    tr.dataset.qaId = item.id || '';
    tr.dataset.qaPriority = String(item.priority ?? 0);
    const questionTd = document.createElement('td');
    const questionInput = document.createElement('textarea');
    questionInput.value = item.question || '';
    questionInput.dataset.qaField = 'question';
    questionInput.rows = 3;
    questionTd.appendChild(questionInput);
    const answerTd = document.createElement('td');
    const answerInput = document.createElement('textarea');
    answerInput.value = item.answer || '';
    answerInput.dataset.qaField = 'answer';
    answerInput.rows = 3;
    answerTd.appendChild(answerInput);
    const priorityTd = document.createElement('td');
    priorityTd.className = 'qa-priority-cell';
    const priorityInput = document.createElement('input');
    priorityInput.type = 'number';
    priorityInput.dataset.qaField = 'priority';
    priorityInput.value = Number.isFinite(item.priority) ? String(item.priority) : String(items.length - index);
    priorityTd.appendChild(priorityInput);
    const actionsTd = document.createElement('td');
    actionsTd.className = 'qa-actions-cell';
    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.textContent = 'Сохранить';
    saveBtn.dataset.action = 'save';
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.textContent = 'Удалить';
    deleteBtn.dataset.action = 'delete';
    const upBtn = document.createElement('button');
    upBtn.type = 'button';
    upBtn.textContent = '↑';
    upBtn.dataset.action = 'move-up';
    if (index === 0) upBtn.disabled = true;
    const downBtn = document.createElement('button');
    downBtn.type = 'button';
    downBtn.textContent = '↓';
    downBtn.dataset.action = 'move-down';
    if (index === items.length - 1) downBtn.disabled = true;
    actionsTd.append(saveBtn, deleteBtn, upBtn, downBtn);
    tr.append(questionTd, answerTd, priorityTd, actionsTd);
    kbTableQa.appendChild(tr);
  });
}

function addQaDraftRow() {
  if (!kbTableQa) return;
  if (!currentProject) {
    if (kbQaStatus) kbQaStatus.textContent = 'Сначала выберите проект';
    setTimeout(() => { if (kbQaStatus) kbQaStatus.textContent = ''; }, 3000);
    return;
  }
  const tr = document.createElement('tr');
  tr.dataset.qaId = `new-${Date.now()}`;
  tr.dataset.qaNew = '1';
  const questionTd = document.createElement('td');
  const questionInput = document.createElement('textarea');
  questionInput.dataset.qaField = 'question';
  questionInput.placeholder = 'Вопрос';
  questionTd.appendChild(questionInput);
  const answerTd = document.createElement('td');
  const answerInput = document.createElement('textarea');
  answerInput.dataset.qaField = 'answer';
  answerInput.placeholder = 'Ответ';
  answerTd.appendChild(answerInput);
  const priorityTd = document.createElement('td');
  const priorityInput = document.createElement('input');
  priorityInput.type = 'number';
  priorityInput.dataset.qaField = 'priority';
  priorityInput.value = qaPairsCache.length ? String(qaPairsCache[0].priority + 1) : '1';
  priorityTd.appendChild(priorityInput);
  const actionsTd = document.createElement('td');
  actionsTd.className = 'qa-actions-cell';
  const saveBtn = document.createElement('button');
  saveBtn.type = 'button';
  saveBtn.textContent = 'Сохранить';
  saveBtn.dataset.action = 'save';
  const cancelBtn = document.createElement('button');
  cancelBtn.type = 'button';
  cancelBtn.textContent = 'Отмена';
  cancelBtn.dataset.action = 'cancel';
  actionsTd.append(saveBtn, cancelBtn);
  tr.append(questionTd, answerTd, priorityTd, actionsTd);
  const firstRow = kbTableQa.querySelector('tr');
  if (firstRow && firstRow.querySelector('.muted')) {
    kbTableQa.innerHTML = '';
  }
  kbTableQa.insertBefore(tr, kbTableQa.firstChild);
  questionInput.focus();
}

async function loadKnowledgeQa() {
  if (!kbTableQa || knowledgeQaUnavailable) return;
  if (!currentProject) {
    renderQaEmpty('Выберите проект');
    if (kbCountQa) kbCountQa.textContent = '—';
    qaPairsCache = [];
    return;
  }
  try {
    const params = new URLSearchParams();
    params.set('project', currentProject);
    params.set('limit', '500');
    const resp = await fetch(`/api/v1/admin/knowledge/qa?${params.toString()}`);
    if (resp.status === 404) {
      knowledgeQaUnavailable = true;
      renderQaEmpty('Модуль Q&A недоступен');
      qaPairsCache = [];
      if (kbCountQa) kbCountQa.textContent = '0';
      return;
    }
    if (!resp.ok) throw new Error('qa_load_failed');
    const data = await resp.json();
    qaPairsCache = Array.isArray(data.items) ? data.items.slice() : [];
    if (Array.isArray(data.priority) && data.priority.length) {
      renderKnowledgePriority(data.priority);
    }
    renderQaTable(qaPairsCache);
    if (kbCountQa) kbCountQa.textContent = qaPairsCache.length ? String(qaPairsCache.length) : '0';
  } catch (error) {
    console.error('knowledge_qa_load_failed', error);
    renderQaEmpty('Не удалось загрузить вопросы');
    if (kbQaStatus) {
      kbQaStatus.textContent = 'Ошибка загрузки';
      setTimeout(() => { kbQaStatus.textContent = ''; }, 3000);
    }
  }
}

async function saveQaRow(row) {
  if (!row) return;
  const question = row.querySelector('[data-qa-field="question"]').value.trim();
  const answer = row.querySelector('[data-qa-field="answer"]').value.trim();
  const priority = parseInt(row.querySelector('[data-qa-field="priority"]').value || '0', 10) || 0;
  if (!question || !answer) {
    if (kbQaStatus) {
      kbQaStatus.textContent = 'Заполните вопрос и ответ';
      setTimeout(() => { kbQaStatus.textContent = ''; }, 3000);
    }
    return;
  }
  const isNew = row.dataset.qaNew === '1' || !(row.dataset.qaId || '').trim();
  const payload = { question, answer, priority };
  if (kbQaStatus) kbQaStatus.textContent = 'Сохраняем...';
  try {
    if (knowledgeQaUnavailable) return;
    if (isNew) {
      const params = new URLSearchParams();
      if (currentProject) params.set('project', currentProject);
      const query = params.toString();
      const url = query ? `/api/v1/admin/knowledge/qa?${query}` : '/api/v1/admin/knowledge/qa';
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (resp.status === 404) {
        knowledgeQaUnavailable = true;
        if (kbQaStatus) kbQaStatus.textContent = 'Добавление недоступно';
        return;
      }
      if (!resp.ok) throw new Error(await resp.text());
    } else {
      const id = row.dataset.qaId;
      const resp = await fetch(`/api/v1/admin/knowledge/qa/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (resp.status === 404) {
        knowledgeQaUnavailable = true;
        if (kbQaStatus) kbQaStatus.textContent = 'Изменение недоступно';
        return;
      }
      if (!resp.ok) throw new Error(await resp.text());
    }
    if (kbQaStatus) kbQaStatus.textContent = 'Сохранено';
    await loadKnowledgeQa();
  } catch (error) {
    console.error('knowledge_qa_save_failed', error);
    if (kbQaStatus) kbQaStatus.textContent = 'Ошибка сохранения';
  } finally {
    setTimeout(() => { if (kbQaStatus) kbQaStatus.textContent = ''; }, 4000);
  }
}

async function deleteQaRow(row) {
  if (!row) return;
  const id = (row.dataset.qaId || '').trim();
  if (!id || row.dataset.qaNew === '1') {
    row.remove();
    if (!kbTableQa.querySelector('tr')) {
      renderQaEmpty('Добавьте вопросы вручную или импортируйте файл');
    }
    return;
  }
  if (!confirm('Удалить эту пару вопрос-ответ?')) return;
  if (kbQaStatus) kbQaStatus.textContent = 'Удаляем...';
  if (knowledgeQaUnavailable) return;
  try {
    const resp = await fetch(`/api/v1/admin/knowledge/qa/${encodeURIComponent(id)}`, { method: 'DELETE' });
    if (resp.status === 404) {
      knowledgeQaUnavailable = true;
      return;
    }
    if (!resp.ok) throw new Error(await resp.text());
    await loadKnowledgeQa();
    if (kbQaStatus) kbQaStatus.textContent = 'Удалено';
  } catch (error) {
    console.error('knowledge_qa_delete_failed', error);
    if (kbQaStatus) kbQaStatus.textContent = 'Не удалось удалить';
  } finally {
    setTimeout(() => { if (kbQaStatus) kbQaStatus.textContent = ''; }, 4000);
  }
}

async function reorderQaPair(id, direction) {
  if (!id || knowledgeQaUnavailable) return;
  const index = qaPairsCache.findIndex((item) => item.id === id);
  if (index === -1) return;
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= qaPairsCache.length) return;
  const [moved] = qaPairsCache.splice(index, 1);
  qaPairsCache.splice(targetIndex, 0, moved);
  const order = qaPairsCache.map((item) => item.id).filter(Boolean);
  if (!order.length) return;
  if (kbQaStatus) kbQaStatus.textContent = 'Сохраняем порядок...';
  try {
    const params = new URLSearchParams();
    if (currentProject) params.set('project', currentProject);
    const query = params.toString();
    const url = query ? `/api/v1/admin/knowledge/qa/reorder?${query}` : '/api/v1/admin/knowledge/qa/reorder';
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order }),
    });
    if (resp.status === 404) {
      knowledgeQaUnavailable = true;
      if (kbQaStatus) kbQaStatus.textContent = 'Изменение порядка недоступно';
      return;
    }
    if (!resp.ok) throw new Error(await resp.text());
    await loadKnowledgeQa();
    if (kbQaStatus) kbQaStatus.textContent = 'Порядок обновлён';
  } catch (error) {
    console.error('knowledge_qa_reorder_failed', error);
    if (kbQaStatus) kbQaStatus.textContent = 'Не удалось изменить порядок';
  } finally {
    setTimeout(() => { if (kbQaStatus) kbQaStatus.textContent = ''; }, 4000);
  }
}

function renderUnansweredTable(items) {
  if (!kbTableUnanswered) return;
  kbTableUnanswered.innerHTML = '';
  if (!Array.isArray(items) || !items.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 3;
    cell.className = 'muted';
    cell.textContent = currentProject ? 'Пока пусто — все вопросы с ответами' : 'Выберите проект';
    row.appendChild(cell);
    kbTableUnanswered.appendChild(row);
    if (kbCountUnanswered) kbCountUnanswered.textContent = '0';
    return;
  }
  items.forEach((item) => {
    const row = document.createElement('tr');
    const questionTd = document.createElement('td');
    questionTd.textContent = item.question || '';
    const hitsTd = document.createElement('td');
    hitsTd.textContent = String(item.hits || 1);
    const updatedTd = document.createElement('td');
    updatedTd.textContent = formatTimestamp(item.updated_at);
    row.append(questionTd, hitsTd, updatedTd);
    kbTableUnanswered.appendChild(row);
  });
  if (kbCountUnanswered) kbCountUnanswered.textContent = String(items.length);
}

async function loadUnansweredQuestions() {
  if (!kbTableUnanswered || knowledgeUnansweredUnavailable) return;
  if (!currentProject) {
    renderUnansweredTable([]);
    return;
  }
  try {
    const params = new URLSearchParams();
    params.set('project', currentProject);
    const resp = await fetch(`/api/v1/admin/knowledge/unanswered?${params.toString()}`);
    if (resp.status === 404) {
      knowledgeUnansweredUnavailable = true;
      renderUnansweredTable([]);
      if (kbUnansweredStatus) {
        kbUnansweredStatus.textContent = 'Раздел недоступен';
        setTimeout(() => { kbUnansweredStatus.textContent = ''; }, 4000);
      }
      return;
    }
    if (!resp.ok) throw new Error('unanswered_load_failed');
    const data = await resp.json();
    renderUnansweredTable(data.items || []);
  } catch (error) {
    console.error('knowledge_unanswered_load_failed', error);
    renderUnansweredTable([]);
    if (kbUnansweredStatus) {
      kbUnansweredStatus.textContent = 'Ошибка загрузки';
      setTimeout(() => { kbUnansweredStatus.textContent = ''; }, 4000);
    }
  }
}

function resetKnowledgeModal(){
  kbModalId.value = '';
  kbModalName.value = '';
  kbModalUrl.value = '';
  kbModalDesc.value = '';
  kbModalProject.value = currentProject || '';
  kbModalContent.value = '';
  kbModalContent.disabled = false;
  kbModalContent.dataset.binary = '';
  kbModalContent.placeholder = 'Введите текст документа';
  kbModalStatus.textContent = '';
  kbModalCompile.disabled = false;
}

function showKnowledgeModal(){
  kbModalBackdrop.classList.add('show');
}

function hideKnowledgeModal(){
  kbModalBackdrop.classList.remove('show');
  resetKnowledgeModal();
}

async function openKnowledgeModal(fileId){
  resetKnowledgeModal();
  kbModalStatus.textContent = 'Загружаем...';
  try {
    const resp = await fetch(`/api/v1/admin/knowledge/${encodeURIComponent(fileId)}`);
    if (!resp.ok) throw new Error('failed to fetch document');
    const doc = await resp.json();
    kbModalId.value = doc.fileId || fileId;
    kbModalTitle.textContent = doc.name || 'Документ';
    kbModalName.value = doc.name || '';
    kbModalUrl.value = doc.url || '';
    kbModalDesc.value = doc.description || '';
    const projectName = (doc.project || doc.domain || '').toLowerCase();
    kbModalProject.value = projectName;
    if (projectName && currentProject !== projectName) {
      currentProject = projectName;
      projectSelect.value = currentProject;
      updateProjectInputs();
    }
    const contentType = (doc.content_type || '').toLowerCase();
    const isBinary = contentType && !contentType.startsWith('text/');
    kbModalContent.value = isBinary ? '' : (doc.content || '');
    kbModalContent.disabled = !!isBinary;
    kbModalContent.placeholder = isBinary ? 'Содержимое недоступно для бинарных файлов. Изменяйте описание и URL.' : 'Введите текст документа';
    kbModalContent.dataset.binary = isBinary ? '1' : '';
    kbModalCompile.disabled = !!isBinary;
    const status = doc.status || 'не обработано';
    const message = doc.statusMessage || '';
    kbModalStatus.dataset.fileId = doc.fileId || fileId;
    kbModalStatus.textContent = message ? `${status}: ${message}` : `Статус: ${status}`;
    showKnowledgeModal();
  } catch (error) {
    console.error(error);
    kbModalStatus.textContent = 'Не удалось загрузить документ';
    setTimeout(() => { kbModalStatus.textContent = ''; }, 3000);
  }
}

async function saveKnowledgeModal(){
  const fileId = kbModalId.value;
  if (!fileId) return;
  if (kbModalContent.dataset.binary === '1' && !kbModalDesc.value.trim()) {
    kbModalStatus.textContent = 'Описание обязательно для файла или изображения';
    return;
  }
  kbModalStatus.textContent = 'Сохраняем...';
  const payload = {
    name: kbModalName.value,
    url: kbModalUrl.value,
    description: kbModalDesc.value,
    project: kbModalProject.value,
    status: 'edited',
    status_message: 'Изменено вручную',
  };
  if (kbModalContent.dataset.binary !== '1') {
    payload.content = kbModalContent.value;
  }
  try {
    const resp = await fetch(`/api/v1/admin/knowledge/${encodeURIComponent(fileId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    const result = await resp.json();
    if (result.file_id) {
      kbModalId.value = result.file_id;
    }
    if (result.project) {
      currentProject = (result.project || '').toLowerCase();
    }
    kbModalStatus.textContent = 'Сохранено';
    await loadProjectsList();
    await loadKnowledge();
    setTimeout(() => { hideKnowledgeModal(); }, 800);
  } catch (error) {
    console.error(error);
    kbModalStatus.textContent = 'Ошибка сохранения';
  }
}

async function compileKnowledge(){
  kbModalStatus.textContent = 'Запускаем компиляцию...';
  try {
    const resp = await fetch('/api/v1/admin/knowledge/reindex', { method: 'POST' });
    if (!resp.ok) throw new Error('compile failed');
    kbModalStatus.textContent = 'Компиляция запущена';
    setTimeout(() => { kbModalStatus.textContent = ''; }, 2000);
  } catch (error) {
    console.error(error);
    kbModalStatus.textContent = 'Ошибка компиляции';
  }
}

async function loadProjectsList(){
  try {
    const resp = await fetch('/api/v1/admin/projects/names');
    if (!resp.ok) return;
    const data = await resp.json();
    const list = document.getElementById('kbProjectList');
    list.innerHTML = '';
    const names = data.projects || [];
    names.forEach((name) => {
      const normalized = (name || '').toLowerCase();
      const option = document.createElement('option');
      option.value = normalized;
      list.appendChild(option);
    });
    document.getElementById('kbProjectsSummary').textContent = names.length ? `${names.length} проект(ов)` : '—';
    if (!currentProject && names.length) {
      currentProject = (names[0] || '').toLowerCase();
      populateProjectForm(currentProject);
      loadKnowledge();
      pollStatus();
    }
  } catch (error) {
    console.error(error);
  }
}

async function saveKnowledge(e){
  e.preventDefault();
  const projectName = currentProject.trim().toLowerCase();
  if (!projectName) {
    document.getElementById('kbAddStatus').textContent = 'Выберите проект';
    return;
  }
  const name = document.getElementById('kbNewName').value.trim();
  const url = document.getElementById('kbNewUrl').value.trim();
  const description = document.getElementById('kbNewDescription').value.trim();
  const content = document.getElementById('kbNewContent').value;
  const fileInput = document.getElementById('kbNewFile');
  const files = Array.from(fileInput?.files || []);
  const statusLabel = document.getElementById('kbAddStatus');
  let overlayVisible = false;
  let lastGeneratedDescription = '';

  const ensureOverlayHidden = () => {
    if (overlayVisible) {
      hideKnowledgeThinking();
      overlayVisible = false;
    }
  };

  try {
    if (files.length) {
      lastGeneratedDescription = '';
      let uploaded = 0;
      let queuedAutoDescriptions = 0;
      overlayVisible = true;
      showKnowledgeThinking(`Загружаем 1/${files.length}…`);
      for (let idx = 0; idx < files.length; idx += 1) {
        const file = files[idx];
        const fd = new FormData();
        fd.append('project', projectName);
        if (files.length === 1 && name) fd.append('name', name);
        if (files.length === 1 && url) fd.append('url', url);
        if (files.length === 1 && description) fd.append('description', description);
        fd.append('file', file);
        statusLabel.textContent = `Загружаем ${idx + 1}/${files.length}: ${file.name}`;
        updateKnowledgeThinking(`Обрабатываем «${file.name}»…`);
        const resp = await fetch('/api/v1/admin/knowledge/upload', { method: 'POST', body: fd });
        if (!resp.ok) {
          const reason = await resp.text();
          console.error('upload failed', reason);
          statusLabel.textContent = `Ошибка при загрузке ${file.name}`;
          continue;
        }
        const result = await resp.json().catch(() => ({}));
        const generatedDescription = typeof result?.description === 'string' ? result.description : '';
        const pendingAuto = result?.auto_description_pending === true;
        if (pendingAuto) {
          queuedAutoDescriptions += 1;
          renderAutoDescription('Описание появится после обработки');
          updateKnowledgeThinking('Файл добавлен, автоописание в очереди');
        } else if (generatedDescription) {
          lastGeneratedDescription = generatedDescription;
          showKnowledgeDescriptionPreview(generatedDescription);
          renderAutoDescription(generatedDescription);
          if (files.length === 1) {
            document.getElementById('kbNewDescription').value = generatedDescription;
          }
          updateKnowledgeThinking('Описание готово! Обновляем список...');
        } else {
          updateKnowledgeThinking('Файл сохранён. Обновляем список...');
        }
        uploaded += 1;
        if (idx + 1 < files.length) {
          updateKnowledgeThinking(`Обрабатываем ${idx + 2}/${files.length}…`);
        }
      }
      ensureOverlayHidden();
      await loadKnowledge();
      await loadProjectsList();
      await fetchProjectStorage();
      document.getElementById('kbNewName').value = '';
      document.getElementById('kbNewUrl').value = '';
      if (!lastGeneratedDescription) {
        document.getElementById('kbNewDescription').value = '';
      }
      document.getElementById('kbNewContent').value = '';
      if (fileInput) {
        fileInput.value = '';
        updateDropZonePreview(fileInput.files);
      } else {
        updateDropZonePreview();
      }
      if (lastGeneratedDescription) {
        document.getElementById('kbNewDescription').value = lastGeneratedDescription;
        renderAutoDescription(lastGeneratedDescription);
      }
      let resultMsg = `Загружено ${uploaded}/${files.length}`;
      if (queuedAutoDescriptions) {
        resultMsg += ` · в очереди AI: ${queuedAutoDescriptions}`;
      }
      statusLabel.textContent = resultMsg;
      populateProjectForm(currentProject);
      return;
    }

    if (!content.trim()) {
      statusLabel.textContent = 'Добавьте текст или выберите файл';
      return;
    }

    lastGeneratedDescription = '';
    overlayVisible = true;
    showKnowledgeThinking('Сохраняем документ…');
    statusLabel.textContent = 'Сохраняем...';
    const resp = await fetch('/api/v1/admin/knowledge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: name || null,
        content,
        project: projectName || null,
        description: description || null,
        url: url || null,
      }),
    });
    if (!resp.ok) {
      statusLabel.textContent = 'Ошибка сохранения';
      return;
    }
    const result = await resp.json().catch(() => ({}));
    const pendingAuto = result?.auto_description_pending === true;
    const generatedDescription = typeof result?.description === 'string' ? result.description : '';
    if (pendingAuto) {
      showKnowledgeDescriptionPreview('Описание будет сформировано позже');
      renderAutoDescription('Описание появится после обработки');
      statusLabel.textContent = 'Документ сохранён, автоописание в очереди';
      updateKnowledgeThinking('Документ сохранён. Автоописание запланировано.');
    } else if (generatedDescription) {
      lastGeneratedDescription = generatedDescription;
      showKnowledgeDescriptionPreview(generatedDescription);
      renderAutoDescription(generatedDescription);
      document.getElementById('kbNewDescription').value = generatedDescription;
      statusLabel.textContent = 'Описание готово';
      updateKnowledgeThinking('Описание готово! Обновляем список...');
    } else {
      statusLabel.textContent = 'Документ сохранён';
      updateKnowledgeThinking('Готово! Обновляем список...');
    }
    document.getElementById('kbNewName').value = '';
    document.getElementById('kbNewUrl').value = '';
    if (!lastGeneratedDescription) {
      document.getElementById('kbNewDescription').value = '';
    }
    document.getElementById('kbNewContent').value = '';
    if (fileInput) {
      fileInput.value = '';
      updateDropZonePreview(fileInput.files);
    } else {
      updateDropZonePreview();
    }
    if (lastGeneratedDescription) {
      document.getElementById('kbNewDescription').value = lastGeneratedDescription;
      renderAutoDescription(lastGeneratedDescription);
    }
    await loadKnowledge();
    await loadProjectsList();
    await fetchProjectStorage();
    populateProjectForm(currentProject);
  } catch (error) {
    console.error(error);
    statusLabel.textContent = 'Ошибка сохранения';
  } finally {
    ensureOverlayHidden();
  }
}

async function deduplicateKnowledge(){
  if (!kbDedupStatus) return;
  const payload = { project: currentProject || null };
  kbDedupStatus.textContent = currentProject ? 'Ищем дубликаты...' : 'Ищем дубликаты во всех проектах...';
  try {
    const resp = await fetch('/api/v1/admin/knowledge/deduplicate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    const result = await resp.json();
    const removed = result.removed ?? 0;
    const kept = result.kept ?? 0;
    kbDedupStatus.textContent = `Удалено ${removed}, осталось ${kept}`;
    await loadKnowledge();
    if (typeof fetchProjectStorage === 'function') {
      await fetchProjectStorage();
    }
    if (typeof populateProjectForm === 'function') {
      populateProjectForm(currentProject);
    }
    setTimeout(() => { kbDedupStatus.textContent = ''; }, 3000);
  } catch (error) {
    console.error(error);
    kbDedupStatus.textContent = 'Ошибка очистки базы знаний';
    setTimeout(() => { kbDedupStatus.textContent = ''; }, 4000);
  }
}
function setKnowledgeActionStatus(message, duration = 3000) {
  if (!kbClearStatus) return;
  kbClearStatus.textContent = message || '';
  if (duration > 0 && message) {
    setTimeout(() => {
      if (kbClearStatus && kbClearStatus.textContent === message) {
        kbClearStatus.textContent = '';
      }
    }, duration);
  }
}

async function deleteKnowledgeDocument(fileId, projectSlug){
  if (!fileId) return;
  if (!confirm('Удалить документ из базы знаний?')) return;
  setKnowledgeActionStatus('Удаляем документ…', 0);
  try {
    const params = new URLSearchParams();
    if (projectSlug) params.set('project', projectSlug);
    const query = params.toString();
    const url = query
      ? `/api/v1/admin/knowledge/${encodeURIComponent(fileId)}?${query}`
      : `/api/v1/admin/knowledge/${encodeURIComponent(fileId)}`;
    const resp = await fetch(url, { method: 'DELETE' });
    if (!resp.ok) throw new Error(await resp.text());
    setKnowledgeActionStatus('Документ удалён');
    await loadKnowledge();
    await fetchProjectStorage();
    populateProjectForm(currentProject);
  } catch (error) {
    console.error('knowledge_document_delete_failed', error);
    setKnowledgeActionStatus('Ошибка удаления', 4000);
  }
}


async function clearKnowledge(){
  if (!kbClearStatus) return;
  const confirmed = confirm(currentProject ? `Очистить базу для проекта ${currentProject}?` : 'Очистить всю базу знаний?');
  if (!confirmed) return;
  kbClearStatus.textContent = 'Удаляем…';
  try {
    const params = new URLSearchParams();
    if (currentProject) params.set('project', currentProject);
    const resp = await fetch(`/api/v1/admin/knowledge?${params.toString()}`, { method: 'DELETE' });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    kbClearStatus.textContent = `Удалено документов: ${data.documents_removed || 0}`;
    await fetchKnowledge();
    await fetchProjectStorage();
    populateProjectForm(currentProject);
    setTimeout(() => { kbClearStatus.textContent = ''; }, 3000);
  } catch (error) {
    console.error('knowledge_clear_failed', error);
    kbClearStatus.textContent = 'Ошибка очистки';
    setTimeout(() => { kbClearStatus.textContent = ''; }, 4000);
  }
}

document.getElementById('kbForm').addEventListener('submit', (e)=>{ e.preventDefault(); loadKnowledge(); });
document.getElementById('kbClear').addEventListener('click', ()=>{ document.getElementById('kbSearch').value=''; loadKnowledge(); });
document.getElementById('kbReloadProjects').addEventListener('click', async ()=>{
  try {
    await loadProjectsList();
    await fetchProjects();
    await fetchProjectStorage();
    await loadKnowledge();
    populateProjectForm(currentProject);
  } catch (error) {
    console.error('kb_reload_projects_failed', error);
    document.getElementById('kbInfo').textContent = 'Не удалось обновить список проектов';
  }
});
document.getElementById('kbAddForm').addEventListener('submit', saveKnowledge);
document.getElementById('kbResetForm').addEventListener('click', () => {
  document.getElementById('kbNewName').value = '';
  document.getElementById('kbNewUrl').value = '';
  document.getElementById('kbNewDescription').value = '';
  document.getElementById('kbNewContent').value = '';
  const fileInput = document.getElementById('kbNewFile');
  if (fileInput) {
    fileInput.value = '';
    updateDropZonePreview(fileInput.files);
  } else {
    updateDropZonePreview();
  }
  renderAutoDescription('');
  document.getElementById('kbAddStatus').textContent = '';
});
if (kbDedupBtn) {
  kbDedupBtn.addEventListener('click', deduplicateKnowledge);
}
if (kbClearBtn) {
  kbClearBtn.addEventListener('click', clearKnowledge);
}
if (kbDropZone && kbNewFileInput) {
  const highlight = () => kbDropZone.classList.add('drag-over');
  const unhighlight = () => kbDropZone.classList.remove('drag-over');
  kbDropZone.addEventListener('click', () => kbNewFileInput.click());
  ['dragenter', 'dragover'].forEach((evt) => {
    kbDropZone.addEventListener(evt, (event) => {
      event.preventDefault();
      event.stopPropagation();
      highlight();
    });
  });
  ['dragleave', 'dragend'].forEach((evt) => {
    kbDropZone.addEventListener(evt, (event) => {
      event.preventDefault();
      event.stopPropagation();
      unhighlight();
    });
  });
  kbDropZone.addEventListener('drop', (event) => {
    event.preventDefault();
    event.stopPropagation();
    unhighlight();
    const files = event.dataTransfer?.files;
    if (!files || !files.length) return;
    const dt = new DataTransfer();
    Array.from(files).forEach((file) => dt.items.add(file));
    kbNewFileInput.files = dt.files;
    updateDropZonePreview(kbNewFileInput.files);
  });
  kbNewFileInput.addEventListener('change', () => updateDropZonePreview(kbNewFileInput.files));
  updateDropZonePreview(kbNewFileInput.files);
}

if (kbPrioritySave) {
  kbPrioritySave.addEventListener('click', () => {
    saveKnowledgePriority();
  });
}

if (kbQaImportForm) {
  kbQaImportForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!currentProject) {
      if (kbQaStatus) {
        kbQaStatus.textContent = 'Выберите проект';
        setTimeout(() => { kbQaStatus.textContent = ''; }, 3000);
      }
      return;
    }
    const file = kbQaFileInput?.files?.[0];
    if (!file) {
      if (kbQaStatus) {
        kbQaStatus.textContent = 'Выберите файл';
        setTimeout(() => { kbQaStatus.textContent = ''; }, 3000);
      }
      return;
    }
    const fd = new FormData();
    fd.append('file', file);
    fd.append('project', currentProject);
    if (kbQaStatus) kbQaStatus.textContent = 'Импортируем...';
    try {
      const resp = await fetch('/api/v1/admin/knowledge/qa/upload', {
        method: 'POST',
        body: fd,
      });
      if (resp.status === 404) {
        console.info('knowledge_qa_import_unavailable');
        if (kbQaStatus) kbQaStatus.textContent = 'Импорт недоступен';
        return;
      }
      if (!resp.ok) throw new Error(await resp.text());
      kbQaFileInput.value = '';
      await loadKnowledgeQa();
      if (kbQaStatus) kbQaStatus.textContent = 'Импорт выполнен';
    } catch (error) {
      console.error('knowledge_qa_import_failed', error);
      if (kbQaStatus) kbQaStatus.textContent = 'Ошибка импорта';
    } finally {
      setTimeout(() => { if (kbQaStatus) kbQaStatus.textContent = ''; }, 4000);
    }
  });
}

if (kbQaAddRowBtn) {
  kbQaAddRowBtn.addEventListener('click', () => addQaDraftRow());
}

if (kbTableQa) {
  kbTableQa.addEventListener('click', (event) => {
    const actionButton = event.target.closest('button[data-action]');
    if (!actionButton) return;
    const row = actionButton.closest('tr');
    const action = actionButton.dataset.action;
    if (action === 'save') {
      saveQaRow(row);
    } else if (action === 'delete') {
      deleteQaRow(row);
    } else if (action === 'cancel') {
      row.remove();
      if (!kbTableQa.querySelector('tr')) {
        renderQaEmpty('Добавьте вопросы вручную или импортируйте файл');
      }
    } else if (action === 'move-up') {
      reorderQaPair(row?.dataset.qaId || '', -1);
    } else if (action === 'move-down') {
      reorderQaPair(row?.dataset.qaId || '', 1);
    }
  });
}

if (kbUnansweredExportBtn) {
  kbUnansweredExportBtn.addEventListener('click', () => {
    const params = new URLSearchParams();
    if (currentProject) params.set('project', currentProject);
    const query = params.toString();
    const url = query ? `/api/v1/admin/knowledge/unanswered/export?${query}` : '/api/v1/admin/knowledge/unanswered/export';
    window.open(url, '_blank');
  });
}

if (kbUnansweredClearBtn) {
  kbUnansweredClearBtn.addEventListener('click', async () => {
    if (!confirm('Очистить список вопросов без ответа?')) return;
    if (kbUnansweredStatus) kbUnansweredStatus.textContent = 'Очищаем...';
    try {
    if (knowledgeUnansweredUnavailable) return;
    const resp = await fetch('/api/v1/admin/knowledge/unanswered/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: currentProject || null }),
    });
    if (resp.status === 404) {
      knowledgeUnansweredUnavailable = true;
      if (kbUnansweredStatus) kbUnansweredStatus.textContent = 'Очистка недоступна';
      return;
    }
      if (!resp.ok) throw new Error(await resp.text());
      await loadUnansweredQuestions();
      if (kbUnansweredStatus) kbUnansweredStatus.textContent = 'Список очищен';
    } catch (error) {
      console.error('knowledge_unanswered_clear_failed', error);
      if (kbUnansweredStatus) kbUnansweredStatus.textContent = 'Не удалось очистить';
    } finally {
      setTimeout(() => { if (kbUnansweredStatus) kbUnansweredStatus.textContent = ''; }, 4000);
    }
  });
}

kbModalClose.addEventListener('click', hideKnowledgeModal);
kbModalCancel.addEventListener('click', hideKnowledgeModal);
kbModalSave.addEventListener('click', saveKnowledgeModal);
kbModalCompile.addEventListener('click', compileKnowledge);
kbModalBackdrop.addEventListener('click', (event) => {
  if (event.target === kbModalBackdrop) {
    hideKnowledgeModal();
  }
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && kbModalBackdrop.classList.contains('show')) {
    hideKnowledgeModal();
  }
});

function applyProjectTelegramState(data, projectName) {
  if (!projectTelegramStatus) return;
  const running = !!(data && data.running);
  projectTelegramStatus.textContent = running ? 'работает' : 'остановлен';
  if (projectTelegramInfo) {
    if (data && data.token_set) {
      projectTelegramInfo.textContent = `Токен сохранён (${data.token_preview || '***'})`;
    } else if (projectName) {
      projectTelegramInfo.textContent = 'Токен не задан';
    } else {
      projectTelegramInfo.textContent = 'Выберите проект';
    }
    if (data && data.last_error) {
      projectTelegramInfo.textContent += ` • Ошибка: ${data.last_error}`;
    }
  }
  if (projectTelegramAutoStart && data) {
    projectTelegramAutoStart.checked = !!data.auto_start;
  } else if (projectTelegramAutoStart && !projectName) {
    projectTelegramAutoStart.checked = false;
  }
  if (projectTelegramStartBtn) projectTelegramStartBtn.disabled = !projectName || running;
  if (projectTelegramStopBtn) projectTelegramStopBtn.disabled = !projectName || !running;
  if (projectTelegramSaveBtn) projectTelegramSaveBtn.disabled = !projectName;
  if (projectTelegramTokenInput) projectTelegramTokenInput.disabled = !projectName;
  if (projectTelegramAutoStart) projectTelegramAutoStart.disabled = !projectName;
}

function resetProjectTelegramUI() {
  applyProjectTelegramState(null, '');
  if (projectTelegramStatus) projectTelegramStatus.textContent = '—';
  if (projectTelegramInfo) projectTelegramInfo.textContent = 'Выберите проект';
  if (projectTelegramMessage) projectTelegramMessage.textContent = '';
  if (projectTelegramTokenInput) projectTelegramTokenInput.value = '';
}

async function loadProjectTelegramStatus(projectName) {
  if (!projectName) {
    resetProjectTelegramUI();
    return;
  }
  if (projectTelegramMessage) projectTelegramMessage.textContent = 'Обновляем...';
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(projectName)}/telegram`);
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    applyProjectTelegramState(data, projectName);
    if (projectTelegramMessage) projectTelegramMessage.textContent = '';
  } catch (error) {
    console.error(error);
    if (projectTelegramStatus) projectTelegramStatus.textContent = 'ошибка';
    if (projectTelegramMessage) projectTelegramMessage.textContent = 'Не удалось получить статус';
    applyProjectTelegramState(null, projectName);
    if (projectTelegramStartBtn) projectTelegramStartBtn.disabled = !projectName;
  }
}

async function saveProjectTelegramConfig() {
  if (!currentProject) {
    if (projectTelegramMessage) projectTelegramMessage.textContent = 'Выберите проект';
    return;
  }
  if (projectTelegramMessage) projectTelegramMessage.textContent = 'Сохраняем...';
  const payload = {
    token: projectTelegramTokenInput && projectTelegramTokenInput.value ? projectTelegramTokenInput.value : null,
    auto_start: projectTelegramAutoStart ? projectTelegramAutoStart.checked : false,
  };
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/telegram/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    if (projectTelegramTokenInput) projectTelegramTokenInput.value = '';
    if (projectTelegramMessage) projectTelegramMessage.textContent = 'Сохранено';
    await loadProjectTelegramStatus(currentProject);
  } catch (error) {
    console.error(error);
    if (projectTelegramMessage) projectTelegramMessage.textContent = 'Ошибка сохранения';
  }
}

async function startProjectTelegram() {
  if (!currentProject) {
    if (projectTelegramMessage) projectTelegramMessage.textContent = 'Выберите проект';
    return;
  }
  if (projectTelegramMessage) projectTelegramMessage.textContent = 'Запускаем...';
  const payload = {};
  if (projectTelegramTokenInput && projectTelegramTokenInput.value) {
    payload.token = projectTelegramTokenInput.value;
  }
  if (projectTelegramAutoStart) {
    payload.auto_start = projectTelegramAutoStart.checked;
  }
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/telegram/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const msg = await resp.text();
      throw new Error(msg || 'start failed');
    }
    if (projectTelegramTokenInput) projectTelegramTokenInput.value = '';
    if (projectTelegramMessage) projectTelegramMessage.textContent = 'Бот запущен';
    await loadProjectTelegramStatus(currentProject);
  } catch (error) {
    console.error(error);
    if (projectTelegramMessage) projectTelegramMessage.textContent = 'Ошибка запуска';
  }
}

async function stopProjectTelegram() {
  if (!currentProject) {
    if (projectTelegramMessage) projectTelegramMessage.textContent = 'Выберите проект';
    return;
  }
  if (projectTelegramMessage) projectTelegramMessage.textContent = 'Останавливаем...';
  const payload = {};
  if (projectTelegramAutoStart) {
    payload.auto_start = projectTelegramAutoStart.checked;
  }
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/telegram/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    if (projectTelegramMessage) projectTelegramMessage.textContent = 'Бот остановлен';
    await loadProjectTelegramStatus(currentProject);
  } catch (error) {
    console.error(error);
    if (projectTelegramMessage) projectTelegramMessage.textContent = 'Ошибка остановки';
  }
}

if (projectTelegramSaveBtn) projectTelegramSaveBtn.addEventListener('click', saveProjectTelegramConfig);
if (projectTelegramStartBtn) projectTelegramStartBtn.addEventListener('click', startProjectTelegram);
if (projectTelegramStopBtn) projectTelegramStopBtn.addEventListener('click', stopProjectTelegram);

function applyProjectMaxState(data, projectName) {
  const running = data ? !!data.running : false;
  if (projectMaxStatus) projectMaxStatus.textContent = data ? (running ? 'работает' : 'остановлен') : '—';
  if (projectMaxInfo) {
    if (!projectName) {
      projectMaxInfo.textContent = 'Выберите проект';
    } else if (data) {
      const bits = [];
      bits.push(data.token_set ? 'Токен настроен' : 'Токен не указан');
      if (data.token_preview) bits.push(`ID: ${data.token_preview}`);
      if (running) bits.push('бот запущен');
      if (data.last_error) bits.push(`Ошибка: ${data.last_error}`);
      projectMaxInfo.textContent = bits.join(' • ');
    } else {
      projectMaxInfo.textContent = 'Нет данных';
    }
  }
  if (projectMaxAutoStart && data) {
    projectMaxAutoStart.checked = !!data.auto_start;
  } else if (projectMaxAutoStart && !projectName) {
    projectMaxAutoStart.checked = false;
  }
  if (projectMaxStartBtn) projectMaxStartBtn.disabled = !projectName || running;
  if (projectMaxStopBtn) projectMaxStopBtn.disabled = !projectName || !running;
  if (projectMaxSaveBtn) projectMaxSaveBtn.disabled = !projectName;
  if (projectMaxTokenInput) projectMaxTokenInput.disabled = !projectName;
  if (projectMaxAutoStart) projectMaxAutoStart.disabled = !projectName;
}

function resetProjectMaxUI() {
  applyProjectMaxState(null, '');
  if (projectMaxStatus) projectMaxStatus.textContent = '—';
  if (projectMaxInfo) projectMaxInfo.textContent = 'Выберите проект';
  if (projectMaxMessage) projectMaxMessage.textContent = '';
  if (projectMaxTokenInput) projectMaxTokenInput.value = '';
}

async function loadProjectMaxStatus(projectName) {
  if (!projectName) {
    resetProjectMaxUI();
    return;
  }
  if (projectMaxMessage) projectMaxMessage.textContent = 'Обновляем...';
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(projectName)}/max`);
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    applyProjectMaxState(data, projectName);
    if (projectMaxMessage) projectMaxMessage.textContent = '';
  } catch (error) {
    console.error(error);
    if (projectMaxStatus) projectMaxStatus.textContent = 'ошибка';
    if (projectMaxMessage) projectMaxMessage.textContent = 'Не удалось получить статус';
    applyProjectMaxState(null, projectName);
    if (projectMaxStartBtn) projectMaxStartBtn.disabled = !projectName;
  }
}

async function saveProjectMaxConfig() {
  if (!currentProject) {
    if (projectMaxMessage) projectMaxMessage.textContent = 'Выберите проект';
    return;
  }
  if (projectMaxMessage) projectMaxMessage.textContent = 'Сохраняем...';
  const payload = {
    token: projectMaxTokenInput && projectMaxTokenInput.value ? projectMaxTokenInput.value : null,
    auto_start: projectMaxAutoStart ? projectMaxAutoStart.checked : false,
  };
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/max/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    if (projectMaxTokenInput) projectMaxTokenInput.value = '';
    if (projectMaxMessage) projectMaxMessage.textContent = 'Сохранено';
    await loadProjectMaxStatus(currentProject);
  } catch (error) {
    console.error(error);
    if (projectMaxMessage) projectMaxMessage.textContent = 'Ошибка сохранения';
  }
}

async function startProjectMax() {
  if (!currentProject) {
    if (projectMaxMessage) projectMaxMessage.textContent = 'Выберите проект';
    return;
  }
  if (projectMaxMessage) projectMaxMessage.textContent = 'Запускаем...';
  const payload = {};
  if (projectMaxTokenInput && projectMaxTokenInput.value) {
    payload.token = projectMaxTokenInput.value;
  }
  if (projectMaxAutoStart) {
    payload.auto_start = projectMaxAutoStart.checked;
  }
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/max/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    if (projectMaxTokenInput) projectMaxTokenInput.value = '';
    if (projectMaxMessage) projectMaxMessage.textContent = 'Бот запущен';
    await loadProjectMaxStatus(currentProject);
  } catch (error) {
    console.error(error);
    if (projectMaxMessage) projectMaxMessage.textContent = 'Ошибка запуска';
  }
}

async function stopProjectMax() {
  if (!currentProject) {
    if (projectMaxMessage) projectMaxMessage.textContent = 'Выберите проект';
    return;
  }
  if (projectMaxMessage) projectMaxMessage.textContent = 'Останавливаем...';
  const payload = {};
  if (projectMaxAutoStart) {
    payload.auto_start = projectMaxAutoStart.checked;
  }
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/max/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    if (projectMaxMessage) projectMaxMessage.textContent = 'Бот остановлен';
    await loadProjectMaxStatus(currentProject);
  } catch (error) {
    console.error(error);
    if (projectMaxMessage) projectMaxMessage.textContent = 'Ошибка остановки';
  }
}

if (projectMaxSaveBtn) projectMaxSaveBtn.addEventListener('click', saveProjectMaxConfig);
if (projectMaxStartBtn) projectMaxStartBtn.addEventListener('click', startProjectMax);
if (projectMaxStopBtn) projectMaxStopBtn.addEventListener('click', stopProjectMax);

function applyProjectVkState(data, projectName) {
  const running = data ? !!data.running : false;
  if (projectVkStatus) projectVkStatus.textContent = data ? (running ? 'работает' : 'остановлен') : '—';
  if (projectVkInfo) {
    if (!projectName) {
      projectVkInfo.textContent = 'Выберите проект';
    } else if (data) {
      const bits = [];
      bits.push(data.token_set ? 'Токен настроен' : 'Токен не указан');
      if (data.token_preview) bits.push(`ID: ${data.token_preview}`);
      if (running) bits.push('бот запущен');
      if (data.last_error) bits.push(`Ошибка: ${data.last_error}`);
      projectVkInfo.textContent = bits.join(' • ');
    } else {
      projectVkInfo.textContent = 'Нет данных';
    }
  }
  if (projectVkAutoStart && data) {
    projectVkAutoStart.checked = !!data.auto_start;
  } else if (projectVkAutoStart && !projectName) {
    projectVkAutoStart.checked = false;
  }
  if (projectVkStartBtn) projectVkStartBtn.disabled = !projectName || running;
  if (projectVkStopBtn) projectVkStopBtn.disabled = !projectName || !running;
  if (projectVkSaveBtn) projectVkSaveBtn.disabled = !projectName;
  if (projectVkTokenInput) projectVkTokenInput.disabled = !projectName;
  if (projectVkAutoStart) projectVkAutoStart.disabled = !projectName;
}

function resetProjectVkUI() {
  applyProjectVkState(null, '');
  if (projectVkStatus) projectVkStatus.textContent = '—';
  if (projectVkInfo) projectVkInfo.textContent = 'Выберите проект';
  if (projectVkMessage) projectVkMessage.textContent = '';
  if (projectVkTokenInput) projectVkTokenInput.value = '';
}

async function loadProjectVkStatus(projectName) {
  if (!projectName) {
    resetProjectVkUI();
    return;
  }
  if (projectVkMessage) projectVkMessage.textContent = 'Обновляем...';
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(projectName)}/vk`);
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    applyProjectVkState(data, projectName);
    if (projectVkMessage) projectVkMessage.textContent = '';
  } catch (error) {
    console.error(error);
    if (projectVkStatus) projectVkStatus.textContent = 'ошибка';
    if (projectVkMessage) projectVkMessage.textContent = 'Не удалось получить статус';
    applyProjectVkState(null, projectName);
    if (projectVkStartBtn) projectVkStartBtn.disabled = !projectName;
  }
}

async function saveProjectVkConfig() {
  if (!currentProject) {
    if (projectVkMessage) projectVkMessage.textContent = 'Выберите проект';
    return;
  }
  if (projectVkMessage) projectVkMessage.textContent = 'Сохраняем...';
  const payload = {
    token: projectVkTokenInput && projectVkTokenInput.value ? projectVkTokenInput.value : null,
    auto_start: projectVkAutoStart ? projectVkAutoStart.checked : false,
  };
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/vk/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    if (projectVkTokenInput) projectVkTokenInput.value = '';
    if (projectVkMessage) projectVkMessage.textContent = 'Сохранено';
    await loadProjectVkStatus(currentProject);
  } catch (error) {
    console.error(error);
    if (projectVkMessage) projectVkMessage.textContent = 'Ошибка сохранения';
  }
}

async function startProjectVk() {
  if (!currentProject) {
    if (projectVkMessage) projectVkMessage.textContent = 'Выберите проект';
    return;
  }
  if (projectVkMessage) projectVkMessage.textContent = 'Запускаем...';
  const payload = {};
  if (projectVkTokenInput && projectVkTokenInput.value) {
    payload.token = projectVkTokenInput.value;
  }
  if (projectVkAutoStart) {
    payload.auto_start = projectVkAutoStart.checked;
  }
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/vk/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    if (projectVkTokenInput) projectVkTokenInput.value = '';
    if (projectVkMessage) projectVkMessage.textContent = 'Бот запущен';
    await loadProjectVkStatus(currentProject);
  } catch (error) {
    console.error(error);
    if (projectVkMessage) projectVkMessage.textContent = 'Ошибка запуска';
  }
}

async function stopProjectVk() {
  if (!currentProject) {
    if (projectVkMessage) projectVkMessage.textContent = 'Выберите проект';
    return;
  }
  if (projectVkMessage) projectVkMessage.textContent = 'Останавливаем...';
  const payload = {};
  if (projectVkAutoStart) {
    payload.auto_start = projectVkAutoStart.checked;
  }
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/vk/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    if (projectVkMessage) projectVkMessage.textContent = 'Бот остановлен';
    await loadProjectVkStatus(currentProject);
  } catch (error) {
    console.error(error);
    if (projectVkMessage) projectVkMessage.textContent = 'Ошибка остановки';
  }
}

if (projectVkSaveBtn) projectVkSaveBtn.addEventListener('click', saveProjectVkConfig);
if (projectVkStartBtn) projectVkStartBtn.addEventListener('click', startProjectVk);
if (projectVkStopBtn) projectVkStopBtn.addEventListener('click', stopProjectVk);

if (statsRefreshBtn) statsRefreshBtn.addEventListener('click', loadRequestStats);
if (statsExportBtn) statsExportBtn.addEventListener('click', exportRequestStats);

function getDefaultWidgetPath(projectName) {
  const normalized = (projectName || '').trim().toLowerCase();
  if (!normalized) return '';
  return `/widget?project=${encodeURIComponent(normalized)}`;
}

function resolveWidgetHref(path) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;
  if (path.startsWith('/')) {
    return `${window.location.origin}${path}`;
  }
  return `${window.location.origin}/${path}`;
}

function refreshProjectWidgetUI() {
  if (!projectWidgetUrl || !projectWidgetLink || !projectWidgetHint || !projectWidgetCopyBtn) return;
  const normalized = (currentProject || '').trim().toLowerCase();
  const customValue = projectWidgetUrl.value.trim();
  const defaultPath = getDefaultWidgetPath(normalized);
  const effectivePath = customValue || defaultPath;
  if (!normalized) {
    projectWidgetLink.href = '#';
    projectWidgetLink.textContent = 'Открыть виджет';
    projectWidgetLink.style.pointerEvents = 'none';
    projectWidgetLink.style.opacity = '0.6';
    projectWidgetCopyBtn.disabled = true;
    projectWidgetHint.textContent = 'Ссылка отображается после выбора проекта';
    return;
  }
  const href = resolveWidgetHref(effectivePath);
  projectWidgetLink.href = href || '#';
  projectWidgetLink.textContent = effectivePath || defaultPath || '—';
  const hasLink = Boolean(effectivePath);
  projectWidgetLink.style.pointerEvents = hasLink ? 'auto' : 'none';
  projectWidgetLink.style.opacity = hasLink ? '1' : '0.6';
  projectWidgetCopyBtn.disabled = !hasLink;
  if (projectWidgetHint) {
    projectWidgetHint.textContent = customValue ? 'Используется сохранённая ссылка' : `По умолчанию: ${defaultPath || '/widget'}`;
  }
}

if (projectWidgetUrl) {
  projectWidgetUrl.addEventListener('input', () => {
    if (projectWidgetMessage) projectWidgetMessage.textContent = '';
    refreshProjectWidgetUI();
  });
}

if (projectWidgetCopyBtn) {
  projectWidgetCopyBtn.addEventListener('click', async () => {
    const defaultPath = getDefaultWidgetPath(currentProject);
    const customValue = projectWidgetUrl ? projectWidgetUrl.value.trim() : '';
    const effectivePath = customValue || defaultPath;
    if (!effectivePath) return;
    const href = resolveWidgetHref(effectivePath);
    try {
      await navigator.clipboard.writeText(href);
      if (projectWidgetMessage) projectWidgetMessage.textContent = 'Скопировано';
    } catch (error) {
      console.error(error);
      if (projectWidgetMessage) projectWidgetMessage.textContent = 'Не удалось скопировать';
    }
    if (projectWidgetMessage) {
      setTimeout(() => { projectWidgetMessage.textContent = ''; }, 2000);
    }
  });
}

const refreshEmotionsHint = (enabled) => {
  if (!projectEmotionsHint) return;
  projectEmotionsHint.textContent = enabled
    ? 'Ответы будут тёплыми и могут включать эмодзи.'
    : 'Ответы будут нейтральными без эмодзи.';
};

const refreshVoiceHint = (enabled) => {
  if (!projectVoiceHint) return;
  projectVoiceHint.textContent = enabled
    ? 'Виджет может показывать анимированного голосового ассистента.'
    : 'Голосовой консультант не будет доступен в виджете.';
  if (projectVoiceModelInput) {
    projectVoiceModelInput.disabled = !enabled;
  }
};

const refreshImageCaptionsHint = (enabled) => {
  if (!projectImageCaptionsHint) return;
  projectImageCaptionsHint.textContent = enabled
    ? 'LLM создаёт короткие подписи для изображений при индексации.'
    : 'Подписи не генерируются, изображения сохраняются без описания.';
};

const refreshSourcesHint = (enabled) => {
  if (!projectSourcesHint) return;
  projectSourcesHint.textContent = enabled
    ? 'После каждого ответа бот покажет ссылки на использованные материалы.'
    : 'Список источников будет скрыт, если пользователь явно не попросит о нём.';
};

const refreshDebugInfoHint = (enabled) => {
  if (!projectDebugInfoHint) return;
  projectDebugInfoHint.textContent = enabled
    ? 'Перед каждым ответом бот отправит служебную справку о запросе.'
    : 'Служебная справка перед ответом отключена.';
};

const refreshDebugHint = (enabled) => {
  if (!projectDebugHint) return;
  projectDebugHint.textContent = enabled
    ? 'После ответа будет приходить подробная сводка (символы, знания, сессия).'
    : 'Финальная отладочная сводка отключена.';
};

const submitProjectForm = () => {
  if (projectForm) {
    projectForm.requestSubmit();
  }
};

if (projectEmotionsInput) {
  projectEmotionsInput.addEventListener('change', () => {
    refreshEmotionsHint(projectEmotionsInput.checked);
    submitProjectForm();
  });
  refreshEmotionsHint(projectEmotionsInput.checked);
}
if (projectVoiceInput) {
  projectVoiceInput.addEventListener('change', () => {
    refreshVoiceHint(projectVoiceInput.checked);
    submitProjectForm();
  });
  refreshVoiceHint(projectVoiceInput.checked);
}
if (projectImageCaptionsInput) {
  projectImageCaptionsInput.addEventListener('change', () => {
    refreshImageCaptionsHint(projectImageCaptionsInput.checked);
    submitProjectForm();
  });
  refreshImageCaptionsHint(projectImageCaptionsInput.checked);
}
if (projectSourcesInput) {
  projectSourcesInput.addEventListener('change', () => {
    refreshSourcesHint(projectSourcesInput.checked);
    submitProjectForm();
  });
  refreshSourcesHint(projectSourcesInput.checked);
}
if (projectDebugInfoInput) {
  projectDebugInfoInput.addEventListener('change', () => {
    refreshDebugInfoHint(projectDebugInfoInput.checked);
    submitProjectForm();
  });
  refreshDebugInfoHint(projectDebugInfoInput.checked);
}
if (projectDebugInput) {
  projectDebugInput.addEventListener('change', () => {
    refreshDebugHint(projectDebugInput.checked);
    submitProjectForm();
  });
  refreshDebugHint(projectDebugInput.checked);
}

refreshProjectWidgetUI();
resetProjectTelegramUI();
resetProjectMaxUI();
resetProjectVkUI();

function refreshMailIntegrationHint() {
  if (!projectMailHint) return;
  const enabled = projectMailEnabled ? projectMailEnabled.checked : false;
  const hasImap = projectMailImapHostInput && projectMailImapHostInput.value.trim().length > 0;
  const hasSmtp = projectMailSmtpHostInput && projectMailSmtpHostInput.value.trim().length > 0;
  if (!hasImap && !hasSmtp) {
    projectMailHint.textContent = 'Укажите параметры IMAP/SMTP, чтобы ассистент мог работать с почтой.';
  } else if (enabled) {
    projectMailHint.textContent = 'Интеграция активна. Ассистент может отправлять и читать почту.';
  } else {
    projectMailHint.textContent = 'Параметры сохранены, но интеграция выключена. Включите переключатель, чтобы активировать почтовый коннектор.';
  }
}

function resetVoiceTrainingUi(message) {
  if (voiceUploadStatus) voiceUploadStatus.textContent = '—';
  if (voiceTrainStatus) voiceTrainStatus.textContent = '—';
  if (voiceTrainingSummary) {
    voiceTrainingSummary.textContent = message || 'Выберите проект, чтобы загрузить дорожки.';
  }
  stopVoiceRecording(true);
  voiceRecorder.uploading = false;
  if (voiceRecordStatus) voiceRecordStatus.textContent = '—';
  voiceSamplesCache = [];
  voiceJobsCache = [];
  if (voiceSamplesContainer) {
    voiceSamplesContainer.innerHTML = '';
    if (voiceSamplesEmpty) {
      voiceSamplesEmpty.textContent = 'Дорожки не загружены.';
      voiceSamplesContainer.appendChild(voiceSamplesEmpty);
    }
  }
  if (voiceTrainButton) voiceTrainButton.disabled = true;
  if (voiceSampleUploadBtn) voiceSampleUploadBtn.disabled = true;
  if (voiceSampleInput) voiceSampleInput.disabled = true;
  if (voiceJobsContainer) voiceJobsContainer.innerHTML = '';
  refreshVoiceTrainingState();
}

function setVoiceRecordStatus(message) {
  if (voiceRecordStatus) voiceRecordStatus.textContent = message;
}

function cleanupVoiceRecorderStream() {
  if (voiceRecorder.stream) {
    try {
      voiceRecorder.stream.getTracks().forEach((track) => track.stop());
    } catch (error) {
      console.warn('voice_record_stream_cleanup_failed', error);
    }
    voiceRecorder.stream = null;
  }
}

function stopVoiceRecording(skipUpload = false) {
  if (!MEDIA_RECORDER_SUPPORTED) return;
  if (voiceRecorder.timer) {
    clearInterval(voiceRecorder.timer);
    voiceRecorder.timer = null;
  }
  voiceRecorder.skipUpload = skipUpload;
  if (voiceRecorder.recorder && voiceRecorder.recorder.state !== 'inactive') {
    try {
      voiceRecorder.recorder.stop();
    } catch (error) {
      console.warn('voice_record_stop_failed', error);
    }
  } else {
    voiceRecorder.active = false;
    cleanupVoiceRecorderStream();
    voiceRecorder.chunks = [];
    if (voiceRecordBtn) voiceRecordBtn.textContent = t('voiceRecordButton');
    refreshVoiceTrainingState();
  }
}

async function uploadRecordedBlob(blob, filename) {
  if (!currentProject) {
    setVoiceRecordStatus('Выберите проект, чтобы добавить запись.');
    return;
  }
  voiceRecorder.uploading = true;
  refreshVoiceTrainingState();
  setVoiceRecordStatus('Загрузка записи…');
  try {
    const formData = new FormData();
    formData.append('project', currentProject);
    const file = new File([blob], filename, { type: blob.type || 'audio/webm' });
    formData.append('files', file);
    const resp = await fetch('/api/v1/voice/samples', {
      method: 'POST',
      body: formData,
    });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    renderVoiceSamples(data.samples || []);
    setVoiceRecordStatus('Запись загружена');
    setTimeout(() => {
      if (!voiceRecorder.active) setVoiceRecordStatus('—');
    }, 4000);
  } catch (error) {
    console.error('voice_record_upload_failed', error);
    setVoiceRecordStatus('Не удалось загрузить запись');
  } finally {
    voiceRecorder.uploading = false;
    refreshVoiceTrainingState();
  }
}

function handleRecorderStop() {
  voiceRecorder.active = false;
  if (voiceRecordBtn) voiceRecordBtn.textContent = t('voiceRecordButton');
  if (voiceRecorder.timer) {
    clearInterval(voiceRecorder.timer);
    voiceRecorder.timer = null;
  }
  cleanupVoiceRecorderStream();
  const recorderInstance = voiceRecorder.recorder;
  voiceRecorder.recorder = null;
  const chunks = voiceRecorder.chunks.splice(0, voiceRecorder.chunks.length);
  if (voiceRecorder.skipUpload || !chunks.length) {
    setVoiceRecordStatus('—');
    voiceRecorder.skipUpload = false;
    refreshVoiceTrainingState();
    return;
  }
  const mime = recorderInstance?.mimeType || 'audio/webm';
  voiceRecorder.recorder = null;
  const blob = new Blob(chunks, { type: mime });
  const ext = mime.includes('mp4') ? 'm4a' : mime.includes('mpeg') ? 'mp3' : 'webm';
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `recording-${timestamp}.${ext}`;
  uploadRecordedBlob(blob, filename);
  refreshVoiceTrainingState();
}

async function startVoiceRecording() {
  if (!MEDIA_RECORDER_SUPPORTED) return;
  if (!currentProject) {
    setVoiceRecordStatus('Выберите проект для записи.');
    return;
  }
  if (voiceRecorder.uploading) {
    setVoiceRecordStatus('Подождите окончания загрузки.');
    return;
  }
  setVoiceRecordStatus('Подготовка микрофона…');
  try {
    if (!voiceRecorder.stream) {
      voiceRecorder.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: { ideal: true },
          noiseSuppression: { ideal: true },
          channelCount: { ideal: 1 },
          sampleRate: { ideal: 44100 },
        },
      });
    }
  } catch (error) {
    console.error('voice_record_permission_failed', error);
    setVoiceRecordStatus('Доступ к микрофону запрещён.');
    cleanupVoiceRecorderStream();
    return;
  }

  const mimeCandidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/mpeg',
  ];
  let options = {};
  const supported = mimeCandidates.find((type) => {
    try {
      return window.MediaRecorder.isTypeSupported(type);
    } catch (error) {
      return false;
    }
  });
  if (supported) options = { mimeType: supported };

  try {
    voiceRecorder.recorder = new MediaRecorder(voiceRecorder.stream, options);
  } catch (error) {
    console.error('voice_record_init_failed', error);
    setVoiceRecordStatus('Не удалось начать запись.');
    cleanupVoiceRecorderStream();
    return;
  }

  voiceRecorder.chunks = [];
  voiceRecorder.skipUpload = false;
  voiceRecorder.recorder.addEventListener('dataavailable', (event) => {
    if (event.data && event.data.size > 0) {
      voiceRecorder.chunks.push(event.data);
    }
  });
  voiceRecorder.recorder.addEventListener('stop', handleRecorderStop);
  voiceRecorder.recorder.addEventListener('error', (event) => {
    console.error('voice_record_recorder_error', event);
    setVoiceRecordStatus('Ошибка при записи.');
  });

  voiceRecorder.startedAt = Date.now();
  voiceRecorder.active = true;
  if (voiceRecordBtn) voiceRecordBtn.textContent = t('voiceRecordStopButton');
  try {
    voiceRecorder.recorder.start();
  } catch (error) {
    console.error('voice_record_start_failed', error);
    setVoiceRecordStatus('Не удалось начать запись.');
    voiceRecorder.active = false;
    voiceRecorder.recorder = null;
    cleanupVoiceRecorderStream();
    refreshVoiceTrainingState();
    return;
  }
  voiceRecorder.timer = setInterval(() => {
    const elapsed = Date.now() - voiceRecorder.startedAt;
    const seconds = Math.floor(elapsed / 1000);
    const minutes = Math.floor(seconds / 60);
    const label = `${minutes.toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
    setVoiceRecordStatus(`Запись ${label}`);
    if (elapsed >= MAX_RECORDING_MS) {
      stopVoiceRecording();
    }
  }, 250);
  refreshVoiceTrainingState();
}


function isVoiceTrainingActive(jobs = voiceJobsCache) {
  return jobs.some((job) => VOICE_ACTIVE_STATUSES.has(String(job.status || '').toLowerCase()));
}

function refreshVoiceTrainingState() {
  const enoughSamples = voiceSamplesCache.length >= VOICE_MIN_SAMPLE_COUNT;
  const activeJob = isVoiceTrainingActive();
  if (voiceTrainButton) {
    voiceTrainButton.disabled = !enoughSamples || activeJob;
  }
  const blockedForJob = activeJob || voiceJobPending;
  if (voiceSampleUploadBtn) {
    voiceSampleUploadBtn.disabled = !currentProject || blockedForJob || voiceRecorder.active || voiceRecorder.uploading;
  }
  if (voiceSampleInput) {
    voiceSampleInput.disabled = !currentProject || voiceRecorder.active;
  }
  if (voiceRecordBtn) {
    if (!MEDIA_RECORDER_SUPPORTED) {
      voiceRecordBtn.disabled = true;
      if (voiceRecordStatus) voiceRecordStatus.textContent = 'Запись не поддерживается в этом браузере.';
    } else if (voiceRecorder.active) {
      voiceRecordBtn.disabled = false;
    voiceRecordBtn.textContent = t('voiceRecordStopButton');
    } else {
      voiceRecordBtn.textContent = t('voiceRecordButton');
      voiceRecordBtn.disabled = !currentProject || blockedForJob || voiceRecorder.uploading;
      if (!currentProject && !voiceRecorder.uploading) {
        setVoiceRecordStatus('Выберите проект для записи.');
      } else if (!voiceRecorder.uploading && voiceRecordStatus && ['Выберите проект для записи.', '—', 'Запись не поддерживается в этом браузере.', 'Подготовка микрофона…'].includes(voiceRecordStatus.textContent) && currentProject) {
        setVoiceRecordStatus('—');
      }
    }
  }
  if (voiceTrainStatus) {
    if (activeJob) {
      voiceTrainStatus.textContent = 'Обучение уже выполняется';
    } else if (!enoughSamples && voiceSamplesCache.length > 0) {
      voiceTrainStatus.textContent = 'Добавьте ещё дорожки';
    } else if (['Обучение уже выполняется', 'Добавьте ещё дорожки'].includes(voiceTrainStatus.textContent)) {
      voiceTrainStatus.textContent = '—';
    }
  }
}

function renderVoiceSamples(samples) {
  voiceSamplesCache = samples;
  if (!voiceSamplesContainer) return;
  voiceSamplesContainer.innerHTML = '';
  if (voiceTrainingSummary) {
    const total = samples.length;
    const remaining = Math.max(0, VOICE_MIN_SAMPLE_COUNT - total);
    voiceTrainingSummary.textContent = remaining > 0
      ? `Загрузите как минимум ${VOICE_MIN_SAMPLE_COUNT} дорожки. Осталось добавить ${remaining}.`
      : 'Собрано достаточно дорожек. Можно запускать обучение.';
  }
  if (!samples.length) {
    if (voiceSamplesEmpty) {
      voiceSamplesEmpty.textContent = 'Дорожки не загружены.';
      voiceSamplesContainer.appendChild(voiceSamplesEmpty);
    }
    refreshVoiceTrainingState();
    return;
  }
  const list = document.createElement('div');
  list.className = 'voice-samples-list';
  samples.forEach((sample) => {
    const row = document.createElement('div');
    row.className = 'voice-sample-row';
    const label = document.createElement('div');
    label.style.display = 'flex';
    label.style.flexDirection = 'column';
    label.style.gap = '2px';
    label.innerHTML = `<strong>${sample.filename}</strong><span class="muted">${formatBytesOptional(sample.sizeBytes || 0)}</span>`;
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.textContent = 'Удалить';
    removeBtn.addEventListener('click', () => deleteVoiceSample(sample.id));
    row.appendChild(label);
    row.appendChild(removeBtn);
    list.appendChild(row);
  });
  voiceSamplesContainer.appendChild(list);
  refreshVoiceTrainingState();
}

function renderVoiceJobs(jobs) {
  voiceJobsCache = jobs;
  if (!voiceJobsContainer) return;
  voiceJobsContainer.innerHTML = '';
  if (!jobs.length) {
    const placeholder = document.createElement('div');
    placeholder.className = 'muted';
    placeholder.textContent = 'История запусков появится после обучения.';
    voiceJobsContainer.appendChild(placeholder);
    refreshVoiceTrainingState();
    return;
  }
  jobs.forEach((job) => {
    const row = document.createElement('div');
    row.className = 'voice-job-entry';
    const statusLabel = document.createElement('div');
    statusLabel.textContent = `${job.status} · ${(job.progress != null ? Math.round(job.progress * 100) : 0)}%`;
    if (job.message) {
      const hint = document.createElement('div');
      hint.className = 'muted';
      hint.textContent = job.message;
      statusLabel.appendChild(document.createElement('br'));
      statusLabel.appendChild(hint);
    }
    const progressContainer = document.createElement('div');
    progressContainer.className = 'voice-progress-bar';
    const progressFill = document.createElement('div');
    progressFill.className = 'voice-progress-fill';
    const pct = job.progress != null ? Math.max(0, Math.min(1, job.progress)) * 100 : 0;
    progressFill.style.width = `${pct}%`;
    progressContainer.appendChild(progressFill);
    row.appendChild(statusLabel);
    row.appendChild(progressContainer);
    voiceJobsContainer.appendChild(row);
  });
  refreshVoiceTrainingState();
}

function clearVoiceJobsPoll() {
  if (voiceJobsPollTimer) {
    clearInterval(voiceJobsPollTimer);
    voiceJobsPollTimer = null;
  }
}

async function refreshVoiceTraining(projectName) {
  clearVoiceJobsPoll();
  if (!projectName) {
    resetVoiceTrainingUi('Выберите проект, чтобы загрузить дорожки.');
    return;
  }
  if (voiceSampleUploadBtn) voiceSampleUploadBtn.disabled = false;
  if (voiceSampleInput) voiceSampleInput.disabled = false;
  try {
    const [samplesRes, jobsRes] = await Promise.all([
      fetch(`/api/v1/voice/samples?project=${encodeURIComponent(projectName)}`),
      fetch(`/api/v1/voice/jobs?project=${encodeURIComponent(projectName)}&limit=5`),
    ]);
    if (!samplesRes.ok) throw new Error('samples_fetch_failed');
    if (!jobsRes.ok) throw new Error('jobs_fetch_failed');
    const samplesData = await samplesRes.json();
    const jobsData = await jobsRes.json();
    renderVoiceSamples(samplesData.samples || []);
    renderVoiceJobs(jobsData.jobs || []);
    const shouldPoll = jobsData.jobs?.length && ['queued', 'preparing', 'training', 'validating'].includes((jobsData.jobs[0]?.status || '').toLowerCase());
    if (shouldPoll) {
      voiceJobsPollTimer = setInterval(() => refreshVoiceTraining(projectName), 5000);
    }
  } catch (error) {
    console.error('voice_training_refresh_failed', error);
    resetVoiceTrainingUi('Не удалось загрузить данные по голосовому обучению.');
  }
}

async function uploadVoiceSamples(projectName) {
  if (!voiceSampleInput || !voiceSampleInput.files?.length) {
    if (voiceUploadStatus) voiceUploadStatus.textContent = 'Выберите файлы для загрузки.';
    return;
  }
  const formData = new FormData();
  formData.append('project', projectName);
  Array.from(voiceSampleInput.files).forEach((file) => formData.append('files', file));
  if (voiceUploadStatus) voiceUploadStatus.textContent = 'Загрузка…';
  try {
    const response = await fetch('/api/v1/voice/samples', {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || 'upload_failed');
    }
    const data = await response.json();
    renderVoiceSamples(data.samples || []);
    voiceSampleInput.value = '';
    if (voiceUploadStatus) voiceUploadStatus.textContent = 'Готово';
  } catch (error) {
    console.error('voice_upload_failed', error);
    if (voiceUploadStatus) voiceUploadStatus.textContent = 'Ошибка при загрузке дорожек';
  }
}

async function deleteVoiceSample(sampleId) {
  if (!currentProject) return;
  try {
    const res = await fetch(`/api/v1/voice/samples/${sampleId}?project=${encodeURIComponent(currentProject)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('delete_failed');
    const data = await res.json();
    renderVoiceSamples(data.samples || []);
  } catch (error) {
    console.error('voice_sample_delete_failed', error);
  }
}

async function triggerVoiceTraining(projectName) {
  voiceJobPending = true;
  refreshVoiceTrainingState();
  if (voiceTrainStatus) voiceTrainStatus.textContent = 'Подготовка…';
  try {
    const formData = new FormData();
    formData.append('project', projectName);
    const res = await fetch('/api/v1/voice/train', {
      method: 'POST',
      body: formData,
    });
    const raw = await res.text();
    let data = {};
    if (raw) {
      try {
        data = JSON.parse(raw);
      } catch (error) {
        console.warn('voice_train_parse_failed', error);
        data = {};
      }
    }
    if (!res.ok) {
      const detail = (data && typeof data === 'object' && data.detail) ? data.detail : raw;
      if (res.status === 409) {
        if (voiceTrainStatus) voiceTrainStatus.textContent = 'Обучение уже выполняется';
        await refreshVoiceTraining(projectName);
        return;
      }
      if (res.status === 400 && (detail || '').startsWith('not_enough_samples')) {
        if (voiceTrainStatus) voiceTrainStatus.textContent = 'Добавьте ещё дорожки';
        await refreshVoiceTraining(projectName);
        return;
      }
      throw new Error(detail || `HTTP ${res.status}`);
    }
    const detail = (data && typeof data === 'object' && data.detail) ? data.detail : '';
    if (detail === 'job_in_progress') {
      if (voiceTrainStatus) voiceTrainStatus.textContent = 'Обучение уже выполняется';
    } else if (detail === 'job_resumed') {
      if (voiceTrainStatus) voiceTrainStatus.textContent = 'Перезапускаем обучение';
    } else {
      if (voiceTrainStatus) voiceTrainStatus.textContent = 'Обучение запущено';
    }
    await refreshVoiceTraining(projectName);
  } catch (error) {
    console.error('voice_train_failed', error);
    if (voiceTrainStatus) voiceTrainStatus.textContent = 'Не удалось запустить обучение';
  } finally {
    voiceJobPending = false;
    refreshVoiceTrainingState();
  }
}
function populateProjectForm(projectName){
  if (mainPromptAiHandler && typeof mainPromptAiHandler.abort === 'function') {
    mainPromptAiHandler.abort();
  }
  const normalized = (projectName || '').trim().toLowerCase();
  const project = projectsCache[normalized] || null;
  if (startUrlInput) {
    startUrlManual = false;
  }
  if (projectWidgetMessage) projectWidgetMessage.textContent = '';
  if (projectTelegramMessage) projectTelegramMessage.textContent = '';
  if (projectTelegramTokenInput) projectTelegramTokenInput.value = '';
  if (projectMaxMessage) projectMaxMessage.textContent = '';
  if (projectMaxTokenInput) projectMaxTokenInput.value = '';
  if (projectVkMessage) projectVkMessage.textContent = '';
  if (projectVkTokenInput) projectVkTokenInput.value = '';
  projectNameInput.value = project ? project.name : normalized;
  projectNameInput.readOnly = !adminSession.is_super;
  projectTitleInput.value = project?.title || '';
  projectDomainInput.value = project?.domain || '';
  populateModelOptions(project?.llm_model || '');
  projectPromptInput.value = project?.llm_prompt || '';
  if (projectPromptRoleSelect) ensurePromptRoleOptions(projectPromptRoleSelect);
  if (projectPromptAiStatus) projectPromptAiStatus.textContent = '—';
  if (mainPromptAiHandler && typeof mainPromptAiHandler.reset === 'function') {
    mainPromptAiHandler.reset();
  }
  if (projectEmotionsInput) {
    const enabled = project?.llm_emotions_enabled !== false;
    projectEmotionsInput.checked = enabled;
    refreshEmotionsHint(enabled);
  }
  if (projectVoiceInput) {
    const voiceEnabled = project?.llm_voice_enabled !== false;
    projectVoiceInput.checked = voiceEnabled;
    refreshVoiceHint(voiceEnabled);
  }
  if (projectVoiceModelInput) {
    projectVoiceModelInput.value = project?.llm_voice_model || '';
    if (projectVoiceInput) {
      projectVoiceModelInput.disabled = !projectVoiceInput.checked;
    }
  }
  if (projectImageCaptionsInput) {
    const captionsEnabled = project?.knowledge_image_caption_enabled !== false;
    projectImageCaptionsInput.checked = captionsEnabled;
    refreshImageCaptionsHint(captionsEnabled);
  }
  if (projectSourcesInput) {
    const sourcesEnabled = project?.llm_sources_enabled ? true : false;
    projectSourcesInput.checked = sourcesEnabled;
    refreshSourcesHint(sourcesEnabled);
  }
  if (projectDebugInfoInput) {
    const infoEnabled = project?.debug_info_enabled !== false;
    projectDebugInfoInput.checked = infoEnabled;
    refreshDebugInfoHint(infoEnabled);
  }
  if (projectDebugInput) {
    const debugEnabled = !!project?.debug_enabled;
    projectDebugInput.checked = debugEnabled;
    refreshDebugHint(debugEnabled);
  }
  const storage = projectStorageCache[normalized] || projectStorageCache.__default__ || null;
  const textBytes = storage ? storage.text_bytes || storage.documents_bytes || 0 : 0;
  const fileBytes = storage ? storage.binary_bytes || 0 : 0;
  const ctxBytes = storage ? storage.context_bytes || 0 : 0;
  const redisBytes = storage ? storage.redis_bytes || 0 : 0;
  if (projectStorageText) projectStorageText.textContent = storage ? formatBytesOptional(textBytes) : '—';
  if (projectStorageFiles) projectStorageFiles.textContent = storage ? formatBytesOptional(fileBytes) : '—';
  if (projectStorageContexts) projectStorageContexts.textContent = storage ? formatBytesOptional(ctxBytes) : '—';
  if (projectStorageRedis) projectStorageRedis.textContent = storage ? formatBytesOptional(redisBytes) : '—';
  if (projectWidgetUrl) {
    projectWidgetUrl.value = project?.widget_url || '';
  }
  if (projectTelegramAutoStart) {
    projectTelegramAutoStart.checked = !!project?.telegram_auto_start;
  }
  if (projectMaxAutoStart) {
    projectMaxAutoStart.checked = !!project?.max_auto_start;
  }
  if (projectVkAutoStart) {
    projectVkAutoStart.checked = !!project?.vk_auto_start;
  }
  if (projectBitrixEnabled) {
    projectBitrixEnabled.checked = !!project?.bitrix_enabled;
  }
  if (projectBitrixWebhookInput) {
    projectBitrixWebhookInput.value = project?.bitrix_webhook_url || '';
  }
  if (projectBitrixHint) {
    if (!project) {
      projectBitrixHint.textContent = 'Webhook используется для запросов модели и хранится на сервере.';
    } else if (project?.bitrix_webhook_url) {
      projectBitrixHint.textContent = project?.bitrix_enabled
        ? 'Webhook сохранён. Измените поле, чтобы обновить значение или оставьте его для работы интеграции.'
        : 'Webhook сохранён, но интеграция выключена. Измените поле или включите интеграцию, чтобы использовать Bitrix.';
    } else {
      projectBitrixHint.textContent = 'Укажите URL вебхука Bitrix24, чтобы включить интеграцию.';
    }
  }
  refreshVoiceTraining(project ? project.name : null);
  if (projectMailEnabled) {
    projectMailEnabled.checked = !!project?.mail_enabled;
  }
  if (projectMailImapHostInput) {
    projectMailImapHostInput.value = project?.mail_imap_host || '';
  }
  if (projectMailImapPortInput) {
    projectMailImapPortInput.value = project?.mail_imap_port != null ? project.mail_imap_port : '';
  }
  if (projectMailImapSslInput) {
    projectMailImapSslInput.checked = project?.mail_imap_ssl !== false;
  }
  if (projectMailSmtpHostInput) {
    projectMailSmtpHostInput.value = project?.mail_smtp_host || '';
  }
  if (projectMailSmtpPortInput) {
    projectMailSmtpPortInput.value = project?.mail_smtp_port != null ? project.mail_smtp_port : '';
  }
  if (projectMailSmtpTlsInput) {
    projectMailSmtpTlsInput.checked = project?.mail_smtp_tls !== false;
  }
  if (projectMailUsernameInput) {
    projectMailUsernameInput.value = project?.mail_username || '';
  }
  if (projectMailPasswordInput) {
    projectMailPasswordInput.value = '';
    projectMailPasswordInput.placeholder = project?.mail_password_set ? 'Пароль сохранён' : 'Пароль';
  }
  if (projectMailFromInput) {
    projectMailFromInput.value = project?.mail_from || '';
  }
  if (projectMailSignatureInput) {
    projectMailSignatureInput.value = project?.mail_signature || '';
  }
  if (projectMailHint) {
    if (!project) {
      projectMailHint.textContent = 'Укажите параметры IMAP/SMTP, чтобы ассистент мог работать с почтой.';
    } else if (project.mail_enabled) {
      projectMailHint.textContent = 'Интеграция активна. Ассистент может отправлять и читать почту.';
    } else if (project.mail_imap_host || project.mail_smtp_host) {
      projectMailHint.textContent = 'Параметры сохранены, но интеграция выключена. Включите переключатель, чтобы активировать почтовый коннектор.';
    } else {
      projectMailHint.textContent = 'Заполните параметры сервера и включите интеграцию, чтобы активировать почтовый коннектор.';
    }
  }
  if (projectAdminSection) {
    projectAdminSection.style.display = project ? 'flex' : 'none';
  }
  if (projectAdminUsernameInput) {
    projectAdminUsernameInput.value = project?.admin_username || '';
    projectAdminUsernameInput.disabled = false;
    projectAdminUsernameInput.readOnly = !adminSession.is_super;
  }
  if (projectAdminPasswordInput) {
    projectAdminPasswordInput.value = '';
    projectAdminPasswordInput.disabled = !project;
    projectAdminPasswordInput.placeholder = adminSession.is_super
      ? 'Оставьте пустым, чтобы не менять'
      : 'Введите новый пароль';
  }
  if (projectAdminHint) {
    if (!project) {
      projectAdminHint.textContent = 'Выберите проект, чтобы управлять учётными данными.';
    } else if (adminSession.is_super) {
      projectAdminHint.textContent = project?.admin_password_set
        ? 'Пароль настроен. Оставьте поле пустым, чтобы не менять.'
        : 'Укажите логин и пароль администратора проекта.';
    } else {
      projectAdminHint.textContent = project?.admin_password_set
        ? 'Введите новый пароль, чтобы сменить текущий.'
        : 'Установите пароль для доступа к админке проекта.';
    }
  }
  if (crawlerProjectLabel) {
    crawlerProjectLabel.textContent = project ? project.name || normalized || '—' : (normalized || '—');
  }
  const metaBits = [];
  if (project?.domain) metaBits.push(`Домен: ${project.domain}`);
  if (project?.llm_model) metaBits.push(`Модель: ${project.llm_model}`);
  if (project) {
    const emoText = project.llm_emotions_enabled === false ? 'Эмоции: выкл' : 'Эмоции: вкл';
    metaBits.push(emoText);
    metaBits.push(project.debug_info_enabled ? 'Справка: вкл' : 'Справка: выкл');
    metaBits.push(project.debug_enabled ? 'Отладка: вкл' : 'Отладка: выкл');
    metaBits.push(project.llm_sources_enabled ? 'Источники: вкл' : 'Источники: выкл');
    metaBits.push(
      project.knowledge_image_caption_enabled === false
        ? 'Подписи изображений: выкл'
        : 'Подписи изображений: вкл'
    );
    const voiceEnabledBit = project.llm_voice_enabled === false ? 'Голосовой режим: выкл' : 'Голосовой режим: вкл';
    if (project.llm_voice_enabled !== false && project.llm_voice_model) {
      metaBits.push(`Голосовая модель: ${project.llm_voice_model}`);
    } else {
      metaBits.push(voiceEnabledBit);
    }
  }
  if (storage && (textBytes || fileBytes || ctxBytes || redisBytes)) {
    metaBits.push(
      `Хранилище: тексты ${formatBytesOptional(textBytes)} · файлы ${formatBytesOptional(fileBytes)} · контексты ${formatBytesOptional(ctxBytes)} · Redis ${formatBytesOptional(redisBytes)}`
    );
  }
  setSummaryProject(project?.title || project?.name || normalized || '—', metaBits.join('\n') || 'Нет выбранного проекта');
  setSummaryPrompt('', [], project ? 'Ожидаем активности модели' : 'Выберите проект, чтобы увидеть активность');
  if (project && project.domain && startUrlInput && !startUrlManual) {
    const normalizedDomain = project.domain.startsWith('http') ? project.domain : `https://${project.domain}`;
    startUrlInput.value = normalizedDomain;
  }
  if (project && startUrlInput && startUrlManual && project.domain && startUrlInput.value === '') {
    startUrlManual = false;
    const normalizedDomain = project.domain.startsWith('http') ? project.domain : `https://${project.domain}`;
    startUrlInput.value = normalizedDomain;
  }
  currentProject = normalized;
  projectSelect.value = currentProject;
  updateProjectInputs();
  projectPromptSaveBtn.disabled = !project;
  if (projectDeleteBtn) {
    projectDeleteBtn.disabled = !project;
  }
  updateProjectDeleteInfo(currentProject);
  refreshProjectWidgetUI();
  loadProjectTelegramStatus(currentProject);
  loadProjectMaxStatus(currentProject);
  loadProjectVkStatus(currentProject);
  loadRequestStats();
  if (currentProject) {
    localStorage.setItem('admin_project', currentProject);
  } else {
    localStorage.removeItem('admin_project');
  }
}

async function fetchProjects(){
  try {
    const resp = await fetch('/api/v1/admin/projects');
    if (!resp.ok) {
      setProjectStatus('Не удалось загрузить проекты', 3000);
      return;
    }
    const data = await resp.json();
    const projects = Array.isArray(data.projects) ? data.projects : [];
    projectSelect.innerHTML = '';
    projectsCache = {};
    lastProjectCount = projects.length;

    if (!projects.length) {
      projectSelect.appendChild(new Option('— нет проектов —', '', true, true));
      projectSelect.disabled = true;
      currentProject = '';
      populateProjectForm('');
      updateProjectSummary();
      projectPromptSaveBtn.disabled = true;
      return;
    }

    const normalizedNames = projects
      .map((project) => normalizeProjectName(project.name))
      .filter(Boolean);
    const uniqueNames = [...new Set(normalizedNames)];

    let selectedKey = '';
    if (currentProject && uniqueNames.includes(currentProject)) {
      selectedKey = currentProject;
    } else if (adminSession.primary_project && uniqueNames.includes(adminSession.primary_project)) {
      selectedKey = adminSession.primary_project;
    } else if (uniqueNames.length) {
      selectedKey = uniqueNames[0];
    }

    projectSelect.disabled = false;
    if (adminSession.is_super) {
      projectSelect.appendChild(new Option('— выберите проект —', '', false, !selectedKey));
    }

    projects.forEach((p, index) => {
      const key = normalizeProjectName(p.name);
      if (!key) {
        return;
      }
      const cleaned = {
        ...p,
        name: key,
        llm_model: typeof p.llm_model === 'string' ? p.llm_model.trim() : p.llm_model,
        widget_url: typeof p.widget_url === 'string' ? p.widget_url.trim() : p.widget_url,
        telegram_auto_start: typeof p.telegram_auto_start === 'boolean' ? p.telegram_auto_start : !!p.telegram_auto_start,
        max_auto_start: typeof p.max_auto_start === 'boolean' ? p.max_auto_start : !!p.max_auto_start,
        llm_emotions_enabled: p.llm_emotions_enabled !== false,
        llm_voice_enabled: p.llm_voice_enabled === undefined ? true : !!p.llm_voice_enabled,
        llm_voice_model: typeof p.llm_voice_model === 'string' ? p.llm_voice_model.trim() : p.llm_voice_model,
        debug_enabled: !!p.debug_enabled,
        debug_info_enabled: p.debug_info_enabled === undefined ? true : !!p.debug_info_enabled,
        knowledge_image_caption_enabled: p.knowledge_image_caption_enabled === undefined ? true : !!p.knowledge_image_caption_enabled,
        admin_username: typeof p.admin_username === 'string' ? p.admin_username.trim() : '',
        admin_password_set: Boolean(p.admin_password_set),
        bitrix_enabled: p.bitrix_enabled === undefined ? false : !!p.bitrix_enabled,
        bitrix_webhook_url: typeof p.bitrix_webhook_url === 'string' ? p.bitrix_webhook_url.trim() : p.bitrix_webhook_url,
        mail_enabled: p.mail_enabled === undefined ? false : !!p.mail_enabled,
        mail_imap_host: typeof p.mail_imap_host === 'string' ? p.mail_imap_host.trim() : '',
        mail_imap_port: typeof p.mail_imap_port === 'number' ? p.mail_imap_port : null,
        mail_imap_ssl: p.mail_imap_ssl === undefined ? true : !!p.mail_imap_ssl,
        mail_smtp_host: typeof p.mail_smtp_host === 'string' ? p.mail_smtp_host.trim() : '',
        mail_smtp_port: typeof p.mail_smtp_port === 'number' ? p.mail_smtp_port : null,
        mail_smtp_tls: p.mail_smtp_tls === undefined ? true : !!p.mail_smtp_tls,
        mail_username: typeof p.mail_username === 'string' ? p.mail_username.trim() : '',
        mail_from: typeof p.mail_from === 'string' ? p.mail_from.trim() : '',
        mail_signature: typeof p.mail_signature === 'string' ? p.mail_signature : '',
        mail_password_set: Boolean(p.mail_password_set),
      };
      delete cleaned.telegram_token;
      projectsCache[key] = cleaned;

      const shouldSelect = key === selectedKey || (!selectedKey && index === 0 && !adminSession.is_super);
      const optionLabel = p.title || p.name || key;
      const option = new Option(optionLabel, key, false, shouldSelect);
      projectSelect.appendChild(option);
      if (shouldSelect) {
        selectedKey = key;
      }
    });

    currentProject = selectedKey;
    populateProjectForm(currentProject);
    updateProjectSummary();
    projectPromptSaveBtn.disabled = !currentProject;
  } catch (error) {
    console.error(error);
    setProjectStatus('Ошибка загрузки проектов', 3000);
  }
}

projectSelect.addEventListener('change', () => {
  currentProject = projectSelect.value.trim().toLowerCase();
  populateProjectForm(currentProject);
  loadKnowledge();
  pollStatus();
});

projectPromptSaveBtn.addEventListener('click', () => {
  if (projectPromptSaveBtn.disabled) return;
  projectForm.requestSubmit();
});

if (projectBitrixEnabled && projectBitrixHint) {
  projectBitrixEnabled.addEventListener('change', () => {
    const hasWebhook = projectBitrixWebhookInput && projectBitrixWebhookInput.value.trim().length > 0;
    if (projectBitrixEnabled.checked) {
      projectBitrixHint.textContent = hasWebhook
        ? 'Интеграция активна. Модель сможет запрашивать Bitrix24.'
        : 'Интеграция включена. Укажите webhook, чтобы запросы выполнялись корректно.';
    } else {
      projectBitrixHint.textContent = hasWebhook
        ? 'Webhook сохранён, но интеграция выключена. Включите переключатель, чтобы использовать Bitrix.'
        : 'Укажите URL вебхука Bitrix24, чтобы включить интеграцию.';
    }
  });
}

if (projectBitrixWebhookInput && projectBitrixHint) {
  projectBitrixWebhookInput.addEventListener('input', () => {
    const hasWebhook = projectBitrixWebhookInput.value.trim().length > 0;
    if (projectBitrixEnabled && projectBitrixEnabled.checked) {
      projectBitrixHint.textContent = hasWebhook
        ? 'Интеграция активна. Модель сможет запрашивать Bitrix24.'
        : 'Интеграция включена. Укажите webhook, чтобы запросы выполнялись корректно.';
    } else {
      projectBitrixHint.textContent = hasWebhook
        ? 'Webhook сохранён, но интеграция выключена. Включите переключатель, чтобы использовать Bitrix.'
        : 'Укажите URL вебхука Bitrix24, чтобы включить интеграцию.';
    }
  });
}

if (projectMailEnabled && projectMailHint) {
  projectMailEnabled.addEventListener('change', () => {
    refreshMailIntegrationHint();
  });
}
[projectMailImapHostInput, projectMailSmtpHostInput].forEach((input) => {
  if (!input || !projectMailHint) return;
  input.addEventListener('input', () => {
    refreshMailIntegrationHint();
  });
});

if (voiceSampleUploadBtn) {
  voiceSampleUploadBtn.addEventListener('click', () => {
    if (!currentProject) {
      if (voiceUploadStatus) voiceUploadStatus.textContent = 'Выберите проект, чтобы загрузить дорожки.';
      return;
    }
    uploadVoiceSamples(currentProject);
  });
}

if (voiceRecordBtn) {
  if (!MEDIA_RECORDER_SUPPORTED) {
    voiceRecordBtn.disabled = true;
    setVoiceRecordStatus('Запись не поддерживается в этом браузере.');
  } else {
    voiceRecordBtn.addEventListener('click', () => {
      if (!currentProject && !voiceRecorder.active) {
        setVoiceRecordStatus('Выберите проект для записи.');
        refreshVoiceTrainingState();
        return;
      }
      if (voiceRecorder.active) {
        stopVoiceRecording();
      } else {
        startVoiceRecording();
      }
    });
  }
}

if (voiceTrainButton) {
  voiceTrainButton.addEventListener('click', () => {
    if (!currentProject) {
      if (voiceTrainStatus) voiceTrainStatus.textContent = 'Выберите проект для обучения.';
      return;
    }
    if (isVoiceTrainingActive()) {
      if (voiceTrainStatus) voiceTrainStatus.textContent = 'Обучение уже выполняется';
      return;
    }
    if (voiceSamplesCache.length < VOICE_MIN_SAMPLE_COUNT) {
      if (voiceTrainStatus) voiceTrainStatus.textContent = 'Добавьте ещё дорожки';
      return;
    }
    triggerVoiceTraining(currentProject);
  });
}

refreshMailIntegrationHint();
refreshVoiceTrainingState();

projectForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const name = projectNameInput.value.trim().toLowerCase();
  if (!name) {
    setProjectStatus('Укажите идентификатор', 3000);
    return;
  }
  const payload = {
    name,
    title: projectTitleInput.value.trim() || null,
    domain: projectDomainInput.value.trim() || null,
    llm_model: projectModelInput.value || null,
    llm_prompt: projectPromptInput.value.trim() || null,
    llm_emotions_enabled: projectEmotionsInput ? projectEmotionsInput.checked : true,
    llm_voice_enabled: projectVoiceInput ? projectVoiceInput.checked : true,
    llm_voice_model: null,
    knowledge_image_caption_enabled: projectImageCaptionsInput ? projectImageCaptionsInput.checked : true,
    llm_sources_enabled: projectSourcesInput ? projectSourcesInput.checked : false,
    debug_info_enabled: projectDebugInfoInput ? projectDebugInfoInput.checked : true,
    debug_enabled: projectDebugInput ? projectDebugInput.checked : false,
    widget_url: projectWidgetUrl && projectWidgetUrl.value.trim() ? projectWidgetUrl.value.trim() : null,
  };
  if (projectBitrixEnabled) {
    payload.bitrix_enabled = projectBitrixEnabled.checked;
  }
  if (projectBitrixWebhookInput) {
    const webhook = projectBitrixWebhookInput.value.trim();
    payload.bitrix_webhook_url = webhook ? webhook : null;
  }
  if (projectMailEnabled) {
    payload.mail_enabled = projectMailEnabled.checked;
  }
  if (projectMailImapHostInput) {
    const imapHost = projectMailImapHostInput.value.trim();
    payload.mail_imap_host = imapHost || null;
  }
  if (projectMailImapPortInput) {
    const portValue = parseInt(projectMailImapPortInput.value, 10);
    payload.mail_imap_port = Number.isFinite(portValue) ? portValue : null;
  }
  if (projectMailImapSslInput) {
    payload.mail_imap_ssl = projectMailImapSslInput.checked;
  }
  if (projectMailSmtpHostInput) {
    const smtpHost = projectMailSmtpHostInput.value.trim();
    payload.mail_smtp_host = smtpHost || null;
  }
  if (projectMailSmtpPortInput) {
    const smtpPort = parseInt(projectMailSmtpPortInput.value, 10);
    payload.mail_smtp_port = Number.isFinite(smtpPort) ? smtpPort : null;
  }
  if (projectMailSmtpTlsInput) {
    payload.mail_smtp_tls = projectMailSmtpTlsInput.checked;
  }
  if (projectMailUsernameInput) {
    const userValue = projectMailUsernameInput.value.trim();
    payload.mail_username = userValue || null;
  }
  if (projectMailFromInput) {
    const fromValue = projectMailFromInput.value.trim();
    payload.mail_from = fromValue || null;
  }
  if (projectMailSignatureInput) {
    const signatureValue = projectMailSignatureInput.value;
    payload.mail_signature = signatureValue ? signatureValue : null;
  }
  if (projectMailPasswordInput) {
    const rawPass = projectMailPasswordInput.value;
    if (rawPass && rawPass.trim()) {
      payload.mail_password = rawPass;
    }
  }
  if (projectVoiceInput && !projectVoiceInput.checked) {
    payload.llm_voice_model = null;
  } else if (projectVoiceModelInput) {
    const voiceModel = projectVoiceModelInput.value.trim();
    payload.llm_voice_model = voiceModel ? voiceModel : null;
  }
  if (adminSession.is_super && projectAdminUsernameInput) {
    const adminUsername = projectAdminUsernameInput.value.trim();
    payload.admin_username = adminUsername || null;
  }
  if (projectAdminPasswordInput) {
    const adminPasswordRaw = projectAdminPasswordInput.value;
    if (adminPasswordRaw && adminPasswordRaw.trim()) {
      payload.admin_password = adminPasswordRaw;
    }
  }
  setProjectStatus('Сохраняем проект...');
  try {
    const resp = await fetch('/api/v1/admin/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      setProjectStatus('Не удалось сохранить проект', 4000);
      return;
    }
    currentProject = name;
    await fetchProjects();
    await loadProjectsList();
    await fetchProjectStorage();
    await loadKnowledge();
    pollStatus();
    setProjectStatus('Сохранено', 2000);
    populateProjectForm(currentProject);
  } catch (error) {
    console.error(error);
    setProjectStatus('Ошибка сохранения', 4000);
  }
});

if (projectDeleteBtn) projectDeleteBtn.addEventListener('click', async () => {
  if (!currentProject) return;
  if (!confirm(`Удалить проект ${currentProject}?`)) return;
  const toDelete = currentProject;
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(toDelete)}`, { method: 'DELETE' });
    if (!resp.ok) {
      setProjectStatus('Не удалось удалить', 4000);
      return;
    }
    const payload = await resp.json().catch(() => ({}));
    delete projectsCache[toDelete];
    currentProject = '';
    await fetchProjects();
    await loadProjectsList();
    await fetchProjectStorage();
    document.getElementById('kbTable').innerHTML = '';
    document.getElementById('kbInfo').textContent = '';
    const removed = payload?.removed || {};
    const parts = [];
    if (typeof removed.documents === 'number') parts.push(`документов: ${removed.documents}`);
    if (typeof removed.files === 'number') parts.push(`файлов: ${removed.files}`);
    if (typeof removed.contexts === 'number') parts.push(`контекстов: ${removed.contexts}`);
    if (typeof removed.stats === 'number') parts.push(`записей статистики: ${removed.stats}`);
    setProjectStatus(parts.length ? `Удалено (${parts.join(', ')})` : 'Удалено', 4000);
    applySessionPermissions();
    updateProjectDeleteInfo(currentProject);
  } catch (error) {
    console.error(error);
    setProjectStatus('Ошибка удаления', 4000);
  }
});

projectTestBtn.addEventListener('click', async () => {
  if (!currentProject) {
    setProjectStatus('Выберите проект', 3000);
    return;
  }
  setProjectStatus('Тестируем сервисы...');
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/test`);
    if (!resp.ok) {
      setProjectStatus('Ошибка теста', 4000);
      return;
    }
    const data = await resp.json();
    const parts = ['mongo', 'redis', 'qdrant'].map((key) => {
      const result = data[key];
      return `${key}: ${result.ok ? 'ok' : 'fail'}${result.error ? ` (${result.error})` : ''}`;
    });
    setProjectStatus(parts.join(' · '), 4000);
  } catch (error) {
    console.error(error);
    setProjectStatus('Ошибка теста', 4000);
  }
});

if (knowledgeServiceApply) {
  knowledgeServiceApply.addEventListener('click', saveKnowledgeServiceState);
}
if (knowledgeServiceRun) {
  knowledgeServiceRun.addEventListener('click', runKnowledgeService);
}
if (knowledgeServiceRefresh) {
  knowledgeServiceRefresh.addEventListener('click', () => fetchKnowledgeServiceStatus(true));
}
if (crawlerResetBtn) {
  crawlerResetBtn.addEventListener('click', () => performCrawlerAction('/reset', 'Счётчики сброшены'));
}
if (crawlerDedupBtn) {
  crawlerDedupBtn.addEventListener('click', () => performCrawlerAction('/deduplicate', 'Дубликаты удалены'));
}
if (ollamaRefreshBtn) {
  ollamaRefreshBtn.addEventListener('click', () => {
    refreshOllamaCatalog(true);
    refreshOllamaServers();
  });
}
if (ollamaServersRefreshBtn) {
  ollamaServersRefreshBtn.addEventListener('click', () => refreshOllamaServers());
}
if (ollamaServerForm) {
  ollamaServerForm.addEventListener('submit', submitOllamaServerForm);
}
if (feedbackRefreshBtn) {
  feedbackRefreshBtn.addEventListener('click', () => fetchFeedbackTasks());
}

ensureBackupTimezones();
setBackupControlsDisabled(true);
updateBackupActionButtons();


const mainPromptAiHandler = initPromptAiControls({
  textarea: projectPromptInput,
  domainInput: projectDomainInput,
  roleSelect: projectPromptRoleSelect,
  button: projectPromptAiBtn,
  status: projectPromptAiStatus,
});
if (mainPromptAiHandler) promptAiHandlers.push(mainPromptAiHandler);

const modalPromptAiHandler = initPromptAiControls({
  textarea: projectModalPrompt,
  domainInput: projectModalDomain,
  roleSelect: projectModalPromptRole,
  button: projectModalPromptAiBtn,
  status: projectModalPromptAiStatus,
});
if (modalPromptAiHandler) promptAiHandlers.push(modalPromptAiHandler);

initLayoutReordering();

bootstrapAdminApp({
  refreshClusterAvailability,
  loadLlmModels,
  refreshOllamaCatalog,
  refreshOllamaServers,
  fetchProjectStorage,
  fetchProjects,
  loadProjectsList,
  loadRequestStats,
  fetchKnowledgeServiceStatus,
  fetchFeedbackTasks,
  populateProjectForm,
  loadKnowledge,
  pollStatus,
  updateProjectSummary,
});

// Controls for LLM config
document.getElementById('saveLLM').addEventListener('click', async () => {
  const base = document.getElementById('ollamaBase').value.trim();
  const model = document.getElementById('ollamaModel').value.trim();
  const payload = { ollama_base: base || null, model: model || null };
  try {
    const r = await fetch('/api/v1/llm/config', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    document.getElementById('pingRes').textContent = r.ok ? 'Saved' : 'Save failed';
  } catch (error) {
    console.error('llm_config_save_failed', error);
    document.getElementById('pingRes').textContent = 'Save failed';
  }
  pollLLM();
});
document.getElementById('pingLLM').addEventListener('click', async () => {
  try {
    const r = await fetch('/api/v1/llm/ping');
    if (!r.ok) {
      document.getElementById('pingRes').textContent = 'Ping failed';
      return;
    }
    const j = await r.json();
    if (!j.enabled) document.getElementById('pingRes').textContent = 'Disabled';
    else document.getElementById('pingRes').textContent = j.reachable ? 'Reachable' : ('Unreachable' + (j.error ? `: ${j.error}` : ''));
  } catch (error) {
    console.error('llm_ping_failed', error);
    document.getElementById('pingRes').textContent = 'Ping failed';
  }
});

document.getElementById('copyLogs').addEventListener('click', async () => {
  const t = document.getElementById('logs').textContent;
  try{ await navigator.clipboard.writeText(t); document.getElementById('logInfo').textContent = 'Copied'; }
  catch{ document.getElementById('logInfo').textContent = 'Copy failed'; }
});
