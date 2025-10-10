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
const knowledgeServiceEndpoints = [
  '/api/v1/knowledge/service',
  '/api/v1/admin/knowledge/service',
  '/api/v1/llm/admin/knowledge/service',
];
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
let feedbackUnavailable = false;
let knowledgePriorityUnavailable = false;
let knowledgeQaUnavailable = false;
let knowledgeUnansweredUnavailable = false;
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
  if (window.BackupModule?.handleLanguageApplied) {
    window.BackupModule.handleLanguageApplied();
  }
  if (window.VoiceModule?.handleLanguageApplied) {
    window.VoiceModule.handleLanguageApplied();
  }
  renderFeedbackTasks(feedbackTasksCache);
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

async function refreshClusterAvailability() {
  try {
    const resp = await fetch('/api/v1/admin/llm/availability');
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
  feedbackTasksList.innerHTML = '<div class="muted">Загрузка…</div>';
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

async function loadKnowledge(projectName) {
  try {
    const url = projectName ? `/api/v1/admin/knowledge?project=${encodeURIComponent(projectName)}` : '/api/v1/admin/knowledge';
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    console.debug('knowledge data', data);
  } catch (error) {
    console.error('knowledge_load_failed', error);
  }
}

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

initLayoutReordering();

bootstrapAdminApp({
  refreshClusterAvailability,
  loadLlmModels,
  refreshOllamaCatalog,
  refreshOllamaServers,
  fetchProjectStorage,
  fetchProjects,
  loadProjectsList,
  loadRequestStats: typeof loadRequestStats === 'function' ? loadRequestStats : undefined,
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
