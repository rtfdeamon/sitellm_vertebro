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
const llmModelEl = document.getElementById('model');
const llmBackendEl = document.getElementById('backend');
const llmDeviceEl = document.getElementById('device');
const ollamaBaseInput = document.getElementById('ollamaBase');
const ollamaModelInput = document.getElementById('ollamaModel');
const llmPingResultEl = document.getElementById('pingRes');
const saveLlmButton = document.getElementById('saveLLM');
const pingLlmButton = document.getElementById('pingLLM');
const copyLogsButton = document.getElementById('copyLogs');
const logsElement = document.getElementById('logs');
const logInfoElement = document.getElementById('logInfo');
const knowledgeServiceEndpoints = [
  '/api/v1/knowledge/service',
  '/api/v1/admin/knowledge/service',
  '/api/v1/llm/admin/knowledge/service',
];
const pollStatusProxy = (...args) => {
  const fn = typeof window.pollStatus === 'function' ? window.pollStatus : null;
  if (!fn) {
    return undefined;
  }
  return fn(...args);
};
const indexUi = window.UIUtils || {};
const formatBytes = indexUi.formatBytes || ((value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let bytes = numeric;
  let unitIndex = 0;
  while (bytes >= 1024 && unitIndex < units.length - 1) {
    bytes /= 1024;
    unitIndex += 1;
  }
  const precision = unitIndex === 0 ? 0 : bytes < 10 ? 1 : 0;
  return `${bytes.toFixed(precision)} ${units[unitIndex]}`;
});
const formatBytesOptional = indexUi.formatBytesOptional || ((value) => {
  const numeric = Number(value || 0);
  return numeric > 0 ? formatBytes(numeric) : '—';
});
const formatTimestamp = indexUi.formatTimestamp || ((value) => {
  if (value === null || value === undefined) return '—';
  let timestamp = Number(value);
  if (!Number.isFinite(timestamp)) return '—';
  if (timestamp < 1e11) timestamp *= 1000;
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString();
});
const pulseCard = indexUi.pulseCard || (() => {});
let activeKnowledgeServiceEndpoint = null;
const clusterWarning = document.getElementById('clusterWarning');

const setKnowledgeServiceControlsDisabled = (disabled) => {
  if (knowledgeServiceToggle) knowledgeServiceToggle.disabled = disabled;
  if (knowledgeServiceApply) knowledgeServiceApply.disabled = disabled;
  if (knowledgeServiceRefresh) knowledgeServiceRefresh.disabled = disabled;
  if (knowledgeServiceMode) knowledgeServiceMode.disabled = disabled;
  if (knowledgeServicePrompt) knowledgeServicePrompt.disabled = disabled;
  if (knowledgeServiceRun) knowledgeServiceRun.disabled = disabled;
};

const logoutButton = document.getElementById('adminLogout');
const LAYOUT_ORDER_STORAGE_KEY = 'admin_layout_order_v1';

const AUTH_CANCELLED_CODE = 'ADMIN_AUTH_CANCELLED';
const ADMIN_AUTH_HEADER_SESSION_KEY = 'admin_auth_header_v1';
const ADMIN_AUTH_USER_STORAGE_KEY = 'admin_auth_user_v1';
const ADMIN_BASE_KEY = window.location.origin.replace(/\/$/, '');
const ADMIN_PROTECTED_PREFIXES = ['/api/v1/admin/', '/api/v1/backup/'];

const {
  clearAuthHeaderForBase,
  setStoredAdminUser,
  requestAdminAuth,
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
window.requestAdminAuth = requestAdminAuth;
window.healthPollTimer = window.healthPollTimer || null;

let feedbackTasksCache = [];
let feedbackTasksList = window.feedbackTasksList || document.getElementById('feedbackTasksList') || null;
window.feedbackTasksList = feedbackTasksList;
let feedbackUnavailable = false;
let knowledgePriorityUnavailable = false;
let knowledgeQaUnavailable = false;
let knowledgeUnansweredUnavailable = false;
let qaPairsCache = [];
let knowledgePriorityOrder = [];
let knowledgeUnansweredItems = [];
let knowledgeUnansweredVisible = false;
let kbNavButtons = [];
let kbSections = [];

const getActiveProjectKey = () => {
  if (typeof currentProject === 'string' && currentProject.trim()) {
    return currentProject.trim();
  }
  return '';
};
let draggingPriorityItem = null;

const summaryState = {
  project: '',
  crawler: '',
  perf: '',
  build: '',
  prompt: '',
  crawlerData: null,
};

let knowledgeInfoSnapshot = null;
let knowledgeProjectSnapshot = null;

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

function handleLanguageApplied() {
  if (window.BackupModule?.handleLanguageApplied) {
    window.BackupModule.handleLanguageApplied();
  }
  if (window.VoiceModule?.handleLanguageApplied) {
    window.VoiceModule.handleLanguageApplied();
  }
  if (window.ProjectsModule?.handleLanguageApplied) {
    window.ProjectsModule.handleLanguageApplied();
  }
  if (window.OllamaModule?.handleLanguageApplied) {
    window.OllamaModule.handleLanguageApplied();
  }
  if (summaryState.crawlerData) {
    const snapshot = {
      ...summaryState.crawlerData,
    };
    summaryState.crawler = '';
    setSummaryCrawler(null, null, snapshot);
  }
  if (typeof global.reapplyCrawlerProgress === 'function') {
    global.reapplyCrawlerProgress();
  }
  renderKnowledgeSummaryFromSnapshot();
  renderFeedbackTasks(feedbackTasksCache);
  renderKnowledgePriority(knowledgePriorityOrder);
  if (kbPriorityStatus) kbPriorityStatus.textContent = '';
  if (kbDropZone) {
    kbDropZoneDefaultText = t('dragFilesHint');
    if (!kbDropZone.classList.contains('has-files')) {
      kbDropZone.textContent = kbDropZoneDefaultText;
    }
  }
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
const kbForm = document.getElementById('kbForm');
const kbProjectInput = document.getElementById('kbProject');
const kbProjectList = document.getElementById('kbProjectList');
const kbReloadProjectsBtn = document.getElementById('kbReloadProjects');
const kbSearchInput = document.getElementById('kbSearch');
const kbLimitInput = document.getElementById('kbLimit');
const kbFilterClearBtn = document.getElementById('kbClear');
const kbInfo = document.getElementById('kbInfo');
const kbProjectsSummary = document.getElementById('kbProjectsSummary');
const kbAddForm = document.getElementById('kbAddForm');
const kbNewNameInput = document.getElementById('kbNewName');
const kbNewUrlInput = document.getElementById('kbNewUrl');
const kbNewDescriptionInput = document.getElementById('kbNewDescription');
const kbDropZone = document.getElementById('kbDropZone');
let kbDropZoneDefaultText = kbDropZone ? kbDropZone.textContent.trim() : '';
let knowledgeDropFiles = [];
const kbNewFileInput = document.getElementById('kbNewFile');
const kbNewContentInput = document.getElementById('kbNewContent');
const kbAddStatus = document.getElementById('kbAddStatus');
const kbResetButton = document.getElementById('kbResetForm');
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
const kbSectionUnanswered = document.getElementById('kbSectionUnanswered');
const kbTabUnanswered = document.getElementById('kbTabUnanswered');
const KB_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'];
const KB_TEXT_LIKE_TYPES = new Set(['application/json', 'application/xml', 'text/csv']);
const KB_STATUS_PENDING = new Set(['pending_auto_description', 'auto_description_in_progress']);
const KNOWLEDGE_SOURCES = [
  { id: 'qa', labelKey: 'knowledgeSourceFaq' },
  { id: 'qdrant', labelKey: 'knowledgeSourceVector' },
  { id: 'mongo', labelKey: 'knowledgeSourceDocsFiles' },
];

applyLanguage(getCurrentLanguage());

const normalizeProjectName = (value) => (typeof value === 'string' ? value.trim().toLowerCase() : '');

const getKnowledgeProjectKey = () => {
  const explicit = normalizeProjectName(kbProjectInput?.value || '');
  return explicit || getActiveProjectKey();
};

const kbTables = {
  text: { body: kbTableText, counter: kbCountText, emptyKey: 'knowledgeTableTextEmpty' },
  docs: { body: kbTableDocs, counter: kbCountDocs, emptyKey: 'knowledgeTableDocsEmpty' },
  images: { body: kbTableImages, counter: kbCountImages, emptyKey: 'knowledgeTableImagesEmpty' },
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
    badge.title = message || t('knowledgeAutoDescriptionPending');
    badge.setAttribute('aria-label', badge.title);
    return badge;
  }
  if (status === 'auto_description_failed') {
    const badge = document.createElement('span');
    badge.className = 'kb-auto-badge failed';
    badge.textContent = 'AI';
    badge.title = message || t('knowledgeAutoDescriptionFailed');
    badge.setAttribute('aria-label', badge.title);
    return badge;
  }
  return null;
};

const createTypeBadge = (category) => {
  if (category === 'text') return null;
  const badge = document.createElement('span');
  badge.className = 'kb-type-badge';
  badge.textContent = t(category === 'images' ? 'knowledgeBadgePhoto' : 'knowledgeBadgeFile');
  return badge;
};

async function refreshClusterAvailability() {
  try {
    const resp = await fetch('/api/v1/admin/llm/availability');
    if (resp.status === 401) {
      if (clusterWarning) {
        clusterWarning.style.display = '';
      }
      return false;
    }
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();
    if (clusterWarning) {
      clusterWarning.style.display = data?.available ? 'none' : '';
    }
    return Boolean(data?.available);
  } catch (error) {
    console.error('cluster_availability_failed', error);
    if (clusterWarning) {
      clusterWarning.style.display = '';
    }
    return false;
  }
}

const LLM_FIELD_PLACEHOLDER = '—';

const setLlmFieldValue = (element, value) => {
  if (!element) return;
  const display =
    value === null || value === undefined || value === ''
      ? LLM_FIELD_PLACEHOLDER
      : String(value);
  element.textContent = display;
  if (element.dataset && Object.prototype.hasOwnProperty.call(element.dataset, 'i18nValue')) {
    element.dataset.i18nValue = display;
  }
};

const setInputValue = (input, value) => {
  if (!input) return;
  const normalized = value === null || value === undefined ? '' : String(value);
  if (input.value !== normalized) {
    input.value = normalized;
  }
};

async function pollLLM() {
  if (
    !llmModelEl &&
    !llmBackendEl &&
    !llmDeviceEl &&
    !ollamaBaseInput &&
    !ollamaModelInput
  ) {
    return;
  }
  try {
    const resp = await fetch('/api/v1/llm/info');
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();
    setLlmFieldValue(llmModelEl, data?.model);
    setLlmFieldValue(llmBackendEl, data?.backend);
    setLlmFieldValue(llmDeviceEl, data?.device);
    setInputValue(ollamaBaseInput, data?.ollama_base);
    if (ollamaModelInput) {
      const targetModel = typeof data?.model === 'string' ? data.model : '';
      setInputValue(ollamaModelInput, targetModel);
    }
  } catch (error) {
    console.error('llm_info_refresh_failed', error);
  }
}
window.pollLLM = pollLLM;

const FEEDBACK_STATUS_LABELS = {
  open: () => t('feedbackStatusOpen'),
  in_progress: () => t('feedbackStatusInProgress'),
  done: () => t('feedbackStatusDone'),
  dismissed: () => t('feedbackStatusDismissed'),
};

function renderFeedbackTasks(tasks) {
  feedbackTasksCache = Array.isArray(tasks) ? tasks : [];
  if (!feedbackTasksList) return;
  feedbackTasksList.innerHTML = '';
  if (!feedbackTasksCache.length) {
    const placeholder = document.createElement('div');
    placeholder.className = 'muted';
    placeholder.textContent = feedbackUnavailable
      ? t('feedbackError')
      : t('feedbackNoItems');
    feedbackTasksList.appendChild(placeholder);
    return;
  }

  feedbackTasksCache.forEach((task) => {
    const row = document.createElement('div');
    row.className = 'feedback-item';

    const messageEl = document.createElement('div');
    messageEl.className = 'feedback-item-message';
    messageEl.textContent = task.message || '—';
    row.appendChild(messageEl);

    const metaEl = document.createElement('div');
    metaEl.className = 'feedback-item-meta';

    const statusKey = String(task.status || 'open').toLowerCase();
    const statusLabelFactory = FEEDBACK_STATUS_LABELS[statusKey];
    const statusLabel = typeof statusLabelFactory === 'function'
      ? statusLabelFactory()
      : statusKey;
    const statusEl = document.createElement('span');
    statusEl.className = `feedback-status feedback-status-${statusKey}`;
    statusEl.textContent = statusLabel;
    metaEl.appendChild(statusEl);

    if (task.project) {
      const projectEl = document.createElement('span');
      projectEl.className = 'feedback-project';
      projectEl.textContent = task.project;
      metaEl.appendChild(projectEl);
    }

    if (task.page) {
      const pageEl = document.createElement('span');
      pageEl.className = 'feedback-page';
      pageEl.textContent = task.page;
      metaEl.appendChild(pageEl);
    }

    const nameContact = [task.name, task.contact].filter(Boolean).join(' · ');
    if (nameContact) {
      const authorEl = document.createElement('span');
      authorEl.className = 'feedback-author';
      authorEl.textContent = nameContact;
      metaEl.appendChild(authorEl);
    }

    if (typeof task.count === 'number' && task.count > 1) {
      const countEl = document.createElement('span');
      countEl.className = 'feedback-count';
      countEl.textContent = `×${task.count}`;
      metaEl.appendChild(countEl);
    }

    const timestampSource =
      task.updated_at ??
      task.created_at ??
      task.updated_at_iso ??
      task.created_at_iso;
    if (timestampSource != null) {
      const tsEl = document.createElement('span');
      tsEl.className = 'feedback-timestamp';
      if (typeof timestampSource === 'string') {
        const parsed = Date.parse(timestampSource);
        tsEl.textContent = Number.isNaN(parsed) ? timestampSource : new Date(parsed).toLocaleString();
      } else {
        tsEl.textContent = formatTimestamp(timestampSource);
      }
      metaEl.appendChild(tsEl);
    }

    row.appendChild(metaEl);

    if (task.note) {
      const noteEl = document.createElement('div');
      noteEl.className = 'feedback-note muted';
      noteEl.textContent = task.note;
      row.appendChild(noteEl);
    }

    feedbackTasksList.appendChild(row);
  });
}

async function fetchFeedbackTasks() {
  if (!feedbackTasksList) return;
  if (!adminSession.is_super) {
    feedbackUnavailable = true;
    renderFeedbackTasks([]);
    return;
  }
  feedbackUnavailable = false;
  feedbackTasksList.innerHTML = `<div class="muted">${t('loadingEllipsis')}</div>`;
  try {
    const resp = await fetch('/api/v1/admin/feedback');
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();
    const tasks = Array.isArray(data?.tasks) ? data.tasks : [];
    renderFeedbackTasks(tasks);
  } catch (error) {
    console.error('feedback_fetch_failed', error);
    feedbackUnavailable = true;
    renderFeedbackTasks([]);
  }
}

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
    a.textContent = t('buttonDownload');
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
  editBtn.textContent = t('buttonEdit');
  if (category !== 'text') {
    editBtn.textContent = t('labelDescription');
    editBtn.title = t('tooltipEditDescription');
  }
  editBtn.addEventListener('click', () => openKnowledgeModal(doc.fileId));
  actionsTd.appendChild(editBtn);

  if (doc.fileId) {
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.textContent = t('buttonDelete');
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

function normalizeKnowledgePriority(order) {
  const known = new Set(KNOWLEDGE_SOURCES.map((item) => item.id));
  const sanitized = Array.isArray(order)
    ? order.map((value) => String(value || '').trim()).filter((value) => known.has(value))
    : [];
  KNOWLEDGE_SOURCES.forEach((source) => {
    if (!sanitized.includes(source.id)) sanitized.push(source.id);
  });
  return sanitized;
}

function renderKnowledgePriority(order) {
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
    label.textContent = t(source.labelKey);
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
}

const renderKnowledgeDocuments = (documents) => {
  knowledgeDocumentsCache = Array.isArray(documents) ? documents.slice() : [];
  const grouped = { text: [], docs: [], images: [] };
  knowledgeDocumentsCache.forEach((doc) => {
    const bucket = getDocCategory(doc);
    if (!grouped[bucket]) grouped[bucket] = [];
    grouped[bucket].push(doc);
  });

  console.debug('knowledge grouped categories', grouped);
  Object.entries(kbTables).forEach(([category, config]) => {
    if (!config?.body) return;
    const items = grouped[category] || [];
    config.body.innerHTML = '';
    if (!items.length) {
      renderEmptyRow(config.body, t(config.emptyKey));
    } else {
      items.forEach((item) => {
        config.body.appendChild(renderKnowledgeRow(item, category));
      });
    }
    if (config?.counter) {
      config.counter.textContent = items.length ? String(items.length) : '0';
    }
  });
};
const getUnansweredTimestampText = (item) => {
  if (!item) return '—';
  const raw =
    item.updated_at ??
    item.updated_at_iso ??
    item.created_at ??
    item.created_at_iso ??
    null;
  if (raw === null || raw === undefined) return '—';
  if (typeof raw === 'number') {
    return formatTimestamp(raw);
  }
  if (typeof raw === 'string') {
    const parsed = Date.parse(raw);
    return Number.isNaN(parsed) ? raw : formatTimestamp(parsed);
  }
  return '—';
};

const renderUnansweredQuestions = (items) => {
  if (!kbTableUnanswered) return;
  knowledgeUnansweredItems = Array.isArray(items) ? items : [];
  kbTableUnanswered.innerHTML = '';
  if (!knowledgeUnansweredItems.length) {
    return;
  }
  knowledgeUnansweredItems.forEach((item) => {
    const row = document.createElement('tr');
    const questionCell = document.createElement('td');
    questionCell.textContent = (item.question || '').trim() || '—';

    const countCell = document.createElement('td');
    const countValue = Number.isFinite(Number(item.count))
      ? Number(item.count)
      : Number.isFinite(Number(item.hits))
        ? Number(item.hits)
        : null;
    countCell.textContent = countValue !== null ? String(countValue) : '—';
    countCell.className = 'nowrap';

    const updatedCell = document.createElement('td');
    updatedCell.textContent = getUnansweredTimestampText(item);
    updatedCell.className = 'nowrap';

    row.append(questionCell, countCell, updatedCell);
    kbTableUnanswered.appendChild(row);
  });
};

const setUnansweredVisibility = (visible) => {
  if (!kbTabUnanswered || !kbSectionUnanswered) return;
  knowledgeUnansweredVisible = Boolean(visible);
  if (visible) {
    kbTabUnanswered.style.display = '';
    kbTabUnanswered.classList.remove('kb-hidden');
    kbTabUnanswered.removeAttribute('aria-hidden');
    kbSectionUnanswered.style.display = '';
    kbSectionUnanswered.classList.remove('kb-hidden');
    kbSectionUnanswered.removeAttribute('aria-hidden');
  } else {
    kbTabUnanswered.style.display = 'none';
    kbTabUnanswered.classList.add('kb-hidden');
    kbTabUnanswered.setAttribute('aria-hidden', 'true');
    kbSectionUnanswered.style.display = 'none';
    kbSectionUnanswered.classList.add('kb-hidden');
    kbSectionUnanswered.setAttribute('aria-hidden', 'true');
    if (kbTableUnanswered) kbTableUnanswered.innerHTML = '';
    if (kbCountUnanswered) kbCountUnanswered.textContent = '—';
    if (kbUnansweredStatus) kbUnansweredStatus.textContent = '';
    if (kbTabUnanswered.classList.contains('active') && typeof activateKnowledgeSection === 'function') {
      activateKnowledgeSection('overview');
    }
  }
  if (kbUnansweredExportBtn) kbUnansweredExportBtn.disabled = !visible;
  if (kbUnansweredClearBtn) kbUnansweredClearBtn.disabled = !visible;
};

async function loadUnansweredQuestions(projectName) {
  if (
    !kbTableUnanswered ||
    !kbCountUnanswered ||
    !kbTabUnanswered ||
    !kbSectionUnanswered ||
    knowledgeUnansweredUnavailable
  ) {
    return;
  }
  const params = new URLSearchParams();
  const projectKey =
    typeof projectName === 'string' && projectName.trim()
      ? normalizeProjectName(projectName)
      : getKnowledgeProjectKey();
  if (projectKey) params.set('project', projectKey);
  const query = params.toString();
  const url = query
    ? `/api/v1/admin/knowledge/unanswered?${query}`
    : '/api/v1/admin/knowledge/unanswered';
  if (kbUnansweredStatus) kbUnansweredStatus.textContent = t('loadingEllipsis');
  try {
    const resp = await fetch(url);
    if (resp.status === 404) {
      knowledgeUnansweredUnavailable = true;
      setUnansweredVisibility(false);
      return;
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const items = Array.isArray(data?.items) ? data.items : [];
    renderUnansweredQuestions(items);
    if (kbCountUnanswered) {
      kbCountUnanswered.textContent = items.length ? String(items.length) : '—';
    }
    if (items.length) {
      setUnansweredVisibility(true);
      if (kbUnansweredStatus) kbUnansweredStatus.textContent = '';
    } else {
      setUnansweredVisibility(false);
    }
  } catch (error) {
    console.error('knowledge_unanswered_fetch_failed', error);
    setUnansweredVisibility(true);
    if (kbUnansweredStatus) {
      kbUnansweredStatus.textContent = t('knowledgeUnansweredLoadError');
    }
  }
}

const getKnowledgePriorityOrder = () => {
  if (!kbPriorityList) return knowledgePriorityOrder;
  const order = Array.from(kbPriorityList.querySelectorAll('.kb-priority-item'))
    .map((item) => item.dataset.source || '')
    .filter(Boolean);
  knowledgePriorityOrder = normalizeKnowledgePriority(order);
  return knowledgePriorityOrder;
};

const renderKnowledgeSummaryFromSnapshot = () => {
  if (kbInfo) {
    if (knowledgeInfoSnapshot) {
      const { total, matched, hasMore } = knowledgeInfoSnapshot;
      const metaBits = [];
      if (Number.isFinite(total)) metaBits.push(t('knowledgeTotalDocs', { value: total }));
      if (Number.isFinite(matched)) metaBits.push(t('knowledgeMatchedDocs', { value: matched }));
      if (hasMore) metaBits.push(t('knowledgeHasMoreDocs'));
      kbInfo.textContent = metaBits.join(' · ') || '—';
    } else {
      kbInfo.textContent = '—';
    }
  }
  if (kbProjectsSummary) {
    if (knowledgeProjectSnapshot) {
      kbProjectsSummary.textContent = t('knowledgeProjectSummary', { value: knowledgeProjectSnapshot });
    } else {
      kbProjectsSummary.textContent = '';
    }
  }
};

async function loadKnowledge(projectName) {
  const targetProject =
    typeof projectName === 'string' && projectName.trim()
      ? normalizeProjectName(projectName)
      : getKnowledgeProjectKey();
  if (kbProjectInput) {
    if (typeof projectName === 'string' && projectName.trim()) {
      kbProjectInput.value = targetProject;
    } else if (!kbProjectInput.value && targetProject) {
      kbProjectInput.value = targetProject;
    }
  }
  const unansweredPromise = loadUnansweredQuestions(targetProject);
  try {
    const params = new URLSearchParams();
    if (targetProject) params.set('project', targetProject);
    const queryValue = (kbSearchInput?.value || '').trim();
    if (queryValue) params.set('q', queryValue);
    const limitValue = parseInt(kbLimitInput?.value, 10);
    if (Number.isFinite(limitValue)) {
      const clampedLimit = Math.min(Math.max(limitValue, 10), 1000);
      params.set('limit', String(clampedLimit));
      if (kbLimitInput && clampedLimit !== limitValue) {
        kbLimitInput.value = String(clampedLimit);
      }
    }
    const query = params.toString();
    const url = query ? `/api/v1/admin/knowledge?${query}` : '/api/v1/admin/knowledge';
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const documents = Array.isArray(data?.documents) ? data.documents : [];
    renderKnowledgeDocuments(documents);
    console.debug('knowledge data', data);

    const total = Number(data?.total);
    const matched = Number(data?.matched);
    const projectLabel = data?.project || targetProject || '';
    knowledgeInfoSnapshot = {
      total: Number.isFinite(total) ? total : null,
      matched: Number.isFinite(matched) ? matched : null,
      hasMore: Boolean(data?.has_more),
    };
    knowledgeProjectSnapshot = projectLabel || null;
    renderKnowledgeSummaryFromSnapshot();
  } catch (error) {
    console.error('knowledge_load_failed', error);
    renderKnowledgeDocuments([]);
    knowledgeInfoSnapshot = null;
    knowledgeProjectSnapshot = null;
    if (kbInfo) kbInfo.textContent = t('knowledgeLoadError');
    if (kbProjectsSummary) kbProjectsSummary.textContent = '';
  }
  try {
    await unansweredPromise;
  } catch {
    // already logged inside loadUnansweredQuestions
  }
  try {
    await unansweredPromise;
  } catch {
    // already logged inside loadUnansweredQuestions
  }
}

async function loadKnowledgePriority(projectName) {
  if (!kbPriorityList || knowledgePriorityUnavailable) return;
  try {
    const params = new URLSearchParams();
    const projectKey =
      typeof projectName === 'string' && projectName.trim()
        ? normalizeProjectName(projectName)
        : getKnowledgeProjectKey();
    if (projectKey) params.set('project', projectKey);
    const query = params.toString();
    const url = query ? `/api/v1/admin/knowledge/priority?${query}` : '/api/v1/admin/knowledge/priority';
    const resp = await fetch(url);
    if (resp.status === 404) {
      knowledgePriorityUnavailable = true;
      renderKnowledgePriority(knowledgePriorityOrder);
      if (kbPriorityStatus) {
        kbPriorityStatus.textContent = t('knowledgePriorityUnavailable');
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
      kbPriorityStatus.textContent = t('knowledgePriorityLoadError');
    }
  }
}

async function saveKnowledgePriority() {
  if (!kbPriorityList || !kbPrioritySave || knowledgePriorityUnavailable) return;
  const order = getKnowledgePriorityOrder();
  if (kbPriorityStatus) {
    kbPriorityStatus.textContent = t('knowledgePrioritySaving');
  }
  kbPrioritySave.disabled = true;
  try {
    const payload = { order };
    const params = new URLSearchParams();
    const projectKey = getKnowledgeProjectKey();
    if (projectKey) params.set('project', projectKey);
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
        kbPriorityStatus.textContent = t('knowledgePrioritySaveUnavailable');
        setTimeout(() => { kbPriorityStatus.textContent = ''; }, 4000);
      }
      return;
    }
    if (!resp.ok) throw new Error(await resp.text());
    if (kbPriorityStatus) {
      kbPriorityStatus.textContent = t('knowledgePrioritySaved');
    }
  } catch (error) {
    console.error('knowledge_priority_save_failed', error);
    if (kbPriorityStatus) {
      kbPriorityStatus.textContent = t('knowledgePrioritySaveError');
    }
  } finally {
    kbPrioritySave.disabled = false;
    setTimeout(() => {
      if (kbPriorityStatus) kbPriorityStatus.textContent = '';
    }, 4000);
  }
}
kbNavButtons = Array.from(document.querySelectorAll('[data-kb-target]'));
kbSections = Array.from(document.querySelectorAll('[data-kb-section]'));

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
  setUnansweredVisibility(knowledgeUnansweredItems.length > 0);

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

if (kbUnansweredExportBtn) {
  kbUnansweredExportBtn.addEventListener('click', () => {
    if (!knowledgeUnansweredVisible || !kbUnansweredExportBtn) return;
    const params = new URLSearchParams();
    const projectKey = getKnowledgeProjectKey();
    if (projectKey) params.set('project', projectKey);
    const query = params.toString();
    const url = query
      ? `/api/v1/admin/knowledge/unanswered/export?${query}`
      : '/api/v1/admin/knowledge/unanswered/export';
    window.open(url, '_blank', 'noopener');
  });
}

if (kbUnansweredClearBtn) {
  kbUnansweredClearBtn.addEventListener('click', async () => {
    if (!knowledgeUnansweredVisible || !adminSession?.can_manage_projects) return;
    const confirmMessage = t('knowledgeUnansweredClearConfirm');
    if (!window.confirm(confirmMessage)) {
      return;
    }
    kbUnansweredClearBtn.disabled = true;
    if (kbUnansweredStatus) kbUnansweredStatus.textContent = t('knowledgeUnansweredClearing');
    try {
      const payload = {};
      const projectKey = getKnowledgeProjectKey();
      if (projectKey) payload.project = projectKey;
      const resp = await fetch('/api/v1/admin/knowledge/unanswered/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json().catch(() => ({}));
      if (kbUnansweredStatus) {
        const removed = Number.isFinite(Number(data?.removed)) ? Number(data.removed) : 0;
        kbUnansweredStatus.textContent = t('knowledgeUnansweredCleared', { value: removed });
      }
      await loadUnansweredQuestions(currentProject);
    } catch (error) {
      console.error('knowledge_unanswered_clear_failed', error);
      if (kbUnansweredStatus) {
        kbUnansweredStatus.textContent = t('knowledgeUnansweredClearError');
      }
    } finally {
      kbUnansweredClearBtn.disabled = !knowledgeUnansweredVisible;
    }
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
  kbAutoDescription.textContent = t('knowledgeAutoDescriptionLabel', { value });
  kbAutoDescription.classList.add('visible');
};

const showKnowledgeThinking = (
  caption = t('knowledgeThinkingCaption'),
  subtitle = t('knowledgeThinkingSubtitle')
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

const WEEK_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;

function updateDropZonePreview(fileList) {
  if (!kbDropZone) return;
  const files = Array.from(fileList || []).filter(Boolean);
  if (!files.length) {
    kbDropZone.textContent = kbDropZoneDefaultText || t('dragFilesHint');
    kbDropZone.classList.remove('has-files');
    return;
  }

  const maxPreview = 4;
  const preview = files.slice(0, maxPreview).map((file) => {
    const size = typeof file.size === 'number' ? ` (${formatBytes(file.size)})` : '';
    return `${file.name}${size}`;
  }).join(', ');
  const remaining = files.length > maxPreview ? `, +${files.length - maxPreview}` : '';
  kbDropZone.textContent = t('knowledgeDropSummary', {
    count: files.length,
    preview,
    remaining,
  });
  kbDropZone.classList.add('has-files');
}

window.updateDropZonePreview = updateDropZonePreview;

const setKnowledgeStatus = (message, isError = false) => {
  if (!kbAddStatus) return;
  kbAddStatus.textContent = message || '';
  kbAddStatus.classList.toggle('status-error', Boolean(isError && message));
};

const setKnowledgeFormDisabled = (disabled) => {
  if (!kbAddForm) return;
  const controls = kbAddForm.querySelectorAll('input, textarea, button');
  controls.forEach((control) => {
    if (control instanceof HTMLButtonElement || control instanceof HTMLInputElement || control instanceof HTMLTextAreaElement) {
      control.disabled = disabled;
    }
  });
};

const resetKnowledgeForm = () => {
  if (kbAddForm) kbAddForm.reset();
  if (kbNewFileInput) {
    kbNewFileInput.value = '';
  }
  knowledgeDropFiles = [];
  updateDropZonePreview([]);
  renderAutoDescription('');
  setKnowledgeStatus('');
};

const refreshKnowledgeProjectsList = async () => {
  if (!kbProjectList) return;
  try {
    const resp = await fetch('/api/v1/admin/projects/names');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const projects = Array.isArray(data?.projects) ? data.projects : [];
    kbProjectList.innerHTML = '';
    const fragment = document.createDocumentFragment();
    projects
      .map((project) => normalizeProjectName(project))
      .filter(Boolean)
      .forEach((project) => {
        const option = document.createElement('option');
        option.value = project;
        fragment.appendChild(option);
      });
    kbProjectList.appendChild(fragment);
    if (kbProjectsSummary) {
      kbProjectsSummary.textContent = projects.length
        ? `${projects.length} projects`
        : '';
    }
  } catch (error) {
    console.error('knowledge_projects_load_failed', error);
    if (kbProjectsSummary) kbProjectsSummary.textContent = '';
  }
};

const toggleDropZoneActive = (active) => {
  if (!kbDropZone) return;
  kbDropZone.classList.toggle('drag-over', Boolean(active));
};

const collectSelectedFiles = () => {
  const fromInput = kbNewFileInput?.files
    ? Array.from(kbNewFileInput.files).filter((file) => file && file.size)
    : [];
  const combined = [...knowledgeDropFiles, ...fromInput];
  if (!combined.length) return [];
  const seen = new Set();
  return combined.filter((file) => {
    if (!file) return false;
    const key = `${file.name || ''}:${file.size || 0}:${file.lastModified || 0}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

async function submitKnowledgeForm(event) {
  event.preventDefault();
  const projectKey = getKnowledgeProjectKey();
  if (!projectKey) {
    setKnowledgeStatus(t('projectsSelectPlaceholder') || 'Select a project first.', true);
    return;
  }

  const textValue = (kbNewContentInput?.value || '').trim();
  const files = collectSelectedFiles();
  if (!textValue && !files.length) {
    setKnowledgeStatus('Add text or select at least one file.', true);
    return;
  }

  setKnowledgeStatus(t('knowledgeServiceSaving') || 'Saving…');
  setKnowledgeFormDisabled(true);

  const descriptionValue = (kbNewDescriptionInput?.value || '').trim();
  const urlValue = (kbNewUrlInput?.value || '').trim();
  const customNameValue = (kbNewNameInput?.value || '').trim();

  let successCount = 0;
  const errors = [];

  try {
    if (textValue) {
      try {
        const payload = {
          project: projectKey,
          content: textValue,
        };
        if (customNameValue) payload.name = customNameValue;
        if (descriptionValue) payload.description = descriptionValue;
        if (urlValue) payload.url = urlValue;
        const resp = await fetch('/api/v1/admin/knowledge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!resp.ok) {
          const message = await resp.text().catch(() => '');
          throw new Error(message || `HTTP ${resp.status}`);
        }
        successCount += 1;
      } catch (error) {
        console.error('knowledge_text_save_failed', error);
        errors.push(t('knowledgeServiceSaveError') || 'Failed to save text document.');
      }
    }

    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('project', projectKey);
        if (descriptionValue) formData.append('description', descriptionValue);
        if (urlValue) formData.append('url', urlValue);
        const effectiveName = files.length === 1 && customNameValue ? customNameValue : (file.name || 'document');
        formData.append('name', effectiveName);
        formData.append('file', file, file.name);
        const resp = await fetch('/api/v1/admin/knowledge/upload', {
          method: 'POST',
          body: formData,
        });
        if (!resp.ok) {
          const message = await resp.text().catch(() => '');
          throw new Error(message || `HTTP ${resp.status}`);
        }
        successCount += 1;
      } catch (error) {
        console.error('knowledge_file_upload_failed', error);
        errors.push(`${file.name || 'file'}: ${(error && error.message) || 'upload failed'}`);
      }
    }

    if (successCount) {
      resetKnowledgeForm();
      await loadKnowledge(projectKey);
      await loadKnowledgePriority(projectKey);
    }

    const successMessage = successCount
      ? successCount === 1
        ? 'Document saved.'
        : `${successCount} items saved.`
      : '';
    const errorMessage = errors.length ? errors.join(' ') : '';
    let finalMessage = successMessage;
    if (errorMessage) {
      finalMessage = finalMessage ? `${finalMessage} ${errorMessage}` : errorMessage;
    }
    if (!finalMessage) {
      finalMessage = 'Nothing to save.';
    }
    const isError = !successCount && Boolean(errorMessage);
    setKnowledgeStatus(finalMessage, isError);
  } finally {
    setKnowledgeFormDisabled(false);
  }
}

if (kbReloadProjectsBtn) {
  kbReloadProjectsBtn.addEventListener('click', () => {
    refreshKnowledgeProjectsList();
  });
}

if (kbForm) {
  kbForm.addEventListener('submit', (event) => {
    event.preventDefault();
    loadKnowledge();
  });
}

if (kbFilterClearBtn) {
  kbFilterClearBtn.addEventListener('click', () => {
    if (kbSearchInput) kbSearchInput.value = '';
    if (kbLimitInput) kbLimitInput.value = '1000';
    loadKnowledge();
  });
}

if (kbNewFileInput) {
  kbNewFileInput.addEventListener('change', () => {
    knowledgeDropFiles = [];
    updateDropZonePreview(kbNewFileInput.files);
  });
}

if (kbNewContentInput) {
  kbNewContentInput.addEventListener('input', () => renderAutoDescription(kbNewContentInput.value));
}

if (kbResetButton) {
  kbResetButton.addEventListener('click', (event) => {
    event.preventDefault();
    resetKnowledgeForm();
  });
}

if (kbAddForm) {
  kbAddForm.addEventListener('submit', submitKnowledgeForm);
}

if (kbDropZone) {
  ['dragenter', 'dragover'].forEach((eventName) => {
    kbDropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      toggleDropZoneActive(true);
    });
  });
  ['dragleave', 'dragend'].forEach((eventName) => {
    kbDropZone.addEventListener(eventName, () => {
      toggleDropZoneActive(false);
    });
  });
  kbDropZone.addEventListener('drop', (event) => {
    event.preventDefault();
    toggleDropZoneActive(false);
    const dropped = Array.from(event.dataTransfer?.files || []).filter(Boolean);
    if (!dropped.length) {
      updateDropZonePreview([]);
      return;
    }
    knowledgeDropFiles = dropped;
    if (kbNewFileInput && typeof DataTransfer !== 'undefined') {
      const buffer = new DataTransfer();
      dropped.forEach((file) => buffer.items.add(file));
      kbNewFileInput.files = buffer.files;
    }
    updateDropZonePreview(dropped);
  });
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
  const parts = [];
  const message = data?.message || (data?.enabled ? t('serviceStateOn') : t('serviceStateOff'));
  if (message) parts.push(message);
  if (typeof data?.enabled === 'boolean') {
    parts.push(data.enabled ? t('serviceStateLabelOn') : t('serviceStateLabelOff'));
  }
  if (typeof data?.mode === 'string') {
    const normalizedMode = data.mode === 'auto'
      ? t('serviceModeAuto')
      : data.mode === 'manual'
        ? t('serviceModeManual')
        : data.mode;
    parts.push(t('serviceModeLabel', { value: normalizedMode }));
  }
  if (typeof data?.running === 'boolean') {
    parts.push(data.running ? t('serviceStatusActive') : t('serviceStatusStopped'));
  }
  if (typeof data?.last_queue === 'number') {
    parts.push(t('knowledgeQueueLabel', { value: data.last_queue }));
  }
  if (typeof data?.idle_seconds === 'number') {
    parts.push(t('knowledgeIdleLabel', { seconds: Math.max(0, Math.round(data.idle_seconds)) }));
  }
  if (data?.last_run_ts) {
    parts.push(t('knowledgeLastRunLabel', { value: formatTimestamp(data.last_run_ts) }));
  }
  if (data?.last_error) {
    parts.push(t('knowledgeErrorLabel', { value: data.last_error }));
  }
  if (data?.manual_reason && data.manual_reason !== 'manual') {
    parts.push(t('knowledgeReasonLabel', { value: data.manual_reason }));
  }
  if (data?.updated_at) {
    parts.push(t('knowledgeUpdatedLabel', { value: formatTimestamp(data.updated_at) }));
  }
  knowledgeServiceStatus.textContent = parts.join(' • ') || '—';
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
  knowledgeServiceStatus.textContent = t('knowledgeProcessingStarting');
  setKnowledgeServiceControlsDisabled(true);
  try {
    const payload = { reason: 'manual_button' };
    const result = await callKnowledgeService('POST', payload, '/run');
    if (result?.error) {
      knowledgeServiceStatus.textContent = t('knowledgeProcessingFailed');
    } else {
      knowledgeServiceStatus.textContent = t('knowledgeProcessingDone');
    }
    await fetchKnowledgeServiceStatus(true);
  } catch (error) {
    console.error('knowledge_service_run_failed', error);
    if (error?.message === 'not_found') {
      knowledgeServiceStatus.textContent = t('knowledgeServiceUpgrade');
    } else {
      knowledgeServiceStatus.textContent = t('knowledgeProcessingStartError');
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

function setSummaryProject(name, meta) {
  const label = name || '—';
  const metaText = meta || t('overviewProjectMeta');
  const signature = `${label}::${metaText}`;
  if (summaryState.project === signature) return;
  summaryState.project = signature;
  summaryProjectEl.textContent = label;
  summaryProjectMeta.textContent = metaText;
  pulseCard(summaryProjectCard);
}

function formatCrawlerSummary(data) {
  if (!data) {
    return { display: '—', meta: '' };
  }
  const normalize = (value) => {
    const num = Number(value ?? 0);
    return Number.isFinite(num) ? num : 0;
  };
  const active = normalize(data.active);
  const queued = normalize(data.queued);
  const done = normalize(data.done);
  const failed = normalize(data.failed);
  const mainLine = `${t('crawlerInProgress', { value: active })} · ${t('crawlerQueued', { value: queued })}`;
  const metaLines = [
    t('crawlerDone', { value: done }),
    t('crawlerFailed', { value: failed }),
  ];
  if (data.lastUrl) {
    metaLines.push(t('crawlerLast', { value: data.lastUrl }));
  }
  if (data.lastRun) {
    metaLines.push(t('crawlerLastRun', { value: data.lastRun }));
  }
  return { display: mainLine, meta: metaLines.join('\n') };
}

function applyCrawlerSummary(display, metaText) {
  const safeDisplay = display || '—';
  const safeMeta = metaText || '';
  const signature = `${safeDisplay}::${safeMeta}`;
  if (summaryState.crawler === signature) return;
  summaryState.crawler = signature;
  summaryCrawlerEl.textContent = safeDisplay;
  summaryCrawlerMeta.textContent = safeMeta;
  pulseCard(summaryCrawlerCard);
}

function setSummaryCrawler(main, meta, rawData = null) {
  if (rawData) {
    summaryState.crawlerData = {
      active: rawData.active ?? 0,
      queued: rawData.queued ?? 0,
      done: rawData.done ?? 0,
      failed: rawData.failed ?? 0,
      lastUrl: rawData.lastUrl || '',
      lastRun: rawData.lastRun || '',
    };
    const { display, meta: metaText } = formatCrawlerSummary(summaryState.crawlerData);
    applyCrawlerSummary(display, metaText);
    return;
  }
  summaryState.crawlerData = null;
  applyCrawlerSummary(main, meta);
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
  const display = text || t('overviewLLMEmpty');
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


if (knowledgeServiceApply) {
  knowledgeServiceApply.addEventListener('click', saveKnowledgeServiceState);
}
if (knowledgeServiceRun) {
  knowledgeServiceRun.addEventListener('click', runKnowledgeService);
}
if (knowledgeServiceRefresh) {
  knowledgeServiceRefresh.addEventListener('click', () => fetchKnowledgeServiceStatus(true));
}
if (feedbackRefreshBtn) {
  feedbackRefreshBtn.addEventListener('click', () => fetchFeedbackTasks());
}

if (kbProjectInput && getActiveProjectKey()) {
  kbProjectInput.value = getActiveProjectKey();
}

initLayoutReordering();

bootstrapAdminApp({
  refreshClusterAvailability,
  loadLlmModels,
  refreshOllamaCatalog,
  refreshOllamaServers,
  renderOllamaCatalogFromCache: typeof window.OllamaModule?.renderCatalogFromCache === 'function'
    ? window.OllamaModule.renderCatalogFromCache
    : undefined,
  renderOllamaServersFromCache: typeof window.OllamaModule?.renderServersFromCache === 'function'
    ? window.OllamaModule.renderServersFromCache
    : undefined,
  fetchProjectStorage,
  fetchProjects,
  loadProjectsList,
  loadRequestStats: typeof loadRequestStats === 'function' ? loadRequestStats : undefined,
  fetchKnowledgeServiceStatus,
  fetchFeedbackTasks,
  populateProjectForm,
  loadKnowledge,
  pollStatus: pollStatusProxy,
  updateProjectSummary,
})
  .then(() => {
    if (kbProjectInput && getActiveProjectKey()) {
      kbProjectInput.value = getActiveProjectKey();
    }
    if (kbProjectList) {
      refreshKnowledgeProjectsList();
    }
  })
  .catch((error) => {
    console.error('bootstrap_init_failed', error);
  });

document.addEventListener('DOMContentLoaded', () => {
  try {
    pollStatusProxy();
  } catch (error) {
    console.error('poll_status_initial_failed', error);
  }
  if (!window.healthPollTimer && typeof window.pollHealth === 'function') {
    window.pollHealth();
    window.healthPollTimer = setInterval(() => {
      const fn = typeof window.pollHealth === 'function' ? window.pollHealth : null;
      if (fn) fn();
    }, 20000);
  }
});

document.addEventListener('admin:poll-status-ready', () => {
  const fn = typeof window.pollStatus === 'function' ? window.pollStatus : null;
  if (fn) {
    try {
      fn();
    } catch (error) {
      console.error('poll_status_initial_failed', error);
    }
  }
  if (!window.healthPollTimer && typeof window.pollHealth === 'function') {
    window.pollHealth();
    window.healthPollTimer = setInterval(() => {
      const pollFn = typeof window.pollHealth === 'function' ? window.pollHealth : null;
      if (pollFn) pollFn();
    }, 20000);
  }
});

// Controls for LLM config
if (saveLlmButton) {
  saveLlmButton.addEventListener('click', async () => {
    const base = ollamaBaseInput ? ollamaBaseInput.value.trim() : '';
    const model = ollamaModelInput ? ollamaModelInput.value.trim() : '';
    const payload = { ollama_base: base || null, model: model || null };
    try {
      const resp = await fetch('/api/v1/llm/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (llmPingResultEl) {
        llmPingResultEl.textContent = resp.ok ? 'Saved' : 'Save failed';
      }
    } catch (error) {
      console.error('llm_config_save_failed', error);
      if (llmPingResultEl) {
        llmPingResultEl.textContent = 'Save failed';
      }
    }
    await pollLLM();
  });
}

if (pingLlmButton) {
  pingLlmButton.addEventListener('click', async () => {
    try {
      const resp = await fetch('/api/v1/llm/ping');
      if (!resp.ok) {
        if (llmPingResultEl) llmPingResultEl.textContent = 'Ping failed';
        return;
      }
      const payload = await resp.json();
      if (!llmPingResultEl) return;
      if (!payload.enabled) {
        llmPingResultEl.textContent = 'Disabled';
      } else if (payload.reachable) {
        llmPingResultEl.textContent = 'Reachable';
      } else {
        const suffix = payload.error ? `: ${payload.error}` : '';
        llmPingResultEl.textContent = `Unreachable${suffix}`;
      }
    } catch (error) {
      console.error('llm_ping_failed', error);
      if (llmPingResultEl) llmPingResultEl.textContent = 'Ping failed';
    }
  });
}

if (copyLogsButton && logsElement && logInfoElement) {
  copyLogsButton.addEventListener('click', async () => {
    const content = logsElement.textContent || '';
    try {
      await navigator.clipboard.writeText(content);
      logInfoElement.textContent = 'Copied';
    } catch {
      logInfoElement.textContent = 'Copy failed';
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    pollLLM();
  });
} else {
  pollLLM();
}
