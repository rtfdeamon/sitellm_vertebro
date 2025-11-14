// Project management module: handles project form orchestration, prompts, widgets, voice training, and related admin helpers.

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
const projectWidgetModalInput = document.getElementById('projectModalWidgetUrl');
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
const projectModalTelegram = document.getElementById('projectModalTelegram');
const projectModalTelegramAuto = document.getElementById('projectModalTelegramAuto');

const projectsUi = window.UIUtils || {};
const formatBytesOptionalFn = projectsUi.formatBytesOptional || ((value) => {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric) || numeric <= 0) return '—';
  if (typeof projectsUi.formatBytes === 'function') {
    return projectsUi.formatBytes(numeric);
  }
  return `${numeric} B`;
});
const getDefaultWidgetPath = projectsUi.getDefaultWidgetPath || ((project) => {
  const slug = typeof project === 'string' ? project.trim().toLowerCase() : '';
  return slug ? `/widget?project=${encodeURIComponent(slug)}` : '';
});
const resolveWidgetHref = projectsUi.resolveWidgetHref || ((path) => path || null);
const voiceModule = window.VoiceModule || null;
const translate = (key, params) => (typeof t === 'function' ? t(key, params) : key);
const safeNormalizeProjectName = (value) => {
  if (typeof globalThis.normalizeProjectName === 'function') {
    try {
      return globalThis.normalizeProjectName(value);
    } catch (error) {
      console.error('normalizeProjectName_failed', error);
    }
  }
  return typeof value === 'string' ? value.trim().toLowerCase() : '';
};
let mainPromptAiHandler = null;

const syncProjectDangerZone = (projectKey) => {
  const canManage = Boolean(window.adminSession?.can_manage_projects);
  const hasProject = Boolean(projectKey);
  if (projectDangerZone) {
    projectDangerZone.classList.toggle('show', canManage && hasProject);
  }
  if (projectDeleteBtn) {
    projectDeleteBtn.disabled = !(canManage && hasProject);
  }
};

syncProjectDangerZone(window.currentProject || '');

const PROMPT_AI_ROLES = [
  {
    value: 'friendly_expert',
    labelKey: 'projectsRoleFriendlyLabel',
    hintKey: 'projectsRoleFriendlyHint',
  },
  {
    value: 'formal_consultant',
    labelKey: 'projectsRoleFormalLabel',
    hintKey: 'projectsRoleFormalHint',
  },
  {
    value: 'sales_manager',
    labelKey: 'projectsRoleManagerLabel',
    hintKey: 'projectsRoleManagerHint',
  },
];

const renderPromptRoleOptions = (select) => {
  if (!select) return;
  const previous = select.value;
  select.innerHTML = '';
  PROMPT_AI_ROLES.forEach((role) => {
    const option = document.createElement('option');
    option.value = role.value;
    option.textContent = t(role.labelKey);
    if (role.hintKey) option.title = t(role.hintKey);
    select.appendChild(option);
  });
  if (previous && Array.from(select.options).some((opt) => opt.value === previous)) {
    select.value = previous;
  } else if (PROMPT_AI_ROLES.length) {
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
    console.log('[projects:buildTargetUrl]', { input: raw, output: parsed.toString() });
    return parsed.toString();
  } catch (error) {
    console.warn('[projects:buildTargetUrl:fail]', { input: raw, error });
    return null;
  }
};

const initPromptAiControls = ({ textarea, domainInput, roleSelect, button, status }) => {
  if (!textarea || !domainInput || !button || !status || !roleSelect) {
    return null;
  }

  console.log('[projects:initPromptAiControls] attach', {
    textarea: textarea.id,
    domainInput: domainInput.id,
    roleSelect: roleSelect.id,
    button: button.id,
    status: status.id,
  });

  renderPromptRoleOptions(roleSelect);
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
      stopGeneration(t('projectsStoppedByInput'));
    }
  });

  button.addEventListener('click', async () => {
    const pageUrl = buildTargetUrl(domainInput.value || projectDomainInput?.value || '');
    console.log('[projects:promptAi:click]', {
      scope: button.id,
      domainValue: domainInput.value,
      fallbackDomain: projectDomainInput?.value,
      pageUrl,
      role: roleSelect.value,
    });
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
        credentials: 'same-origin',
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
      console.log('[projects:promptAi:response]', {
        scope: button.id,
        status: response.status,
        hasPrompt: Boolean(generated),
      });
      if (!generated) {
        setStatus(t('promptAiEmpty'), 4000);
        return;
      }
      textarea.value = generated;
      setStatus(t('promptAiReady'), 2000);
    } catch (error) {
      console.error('prompt_ai_failed', {
        scope: button.id,
        error,
      });
      if (error.name === 'AbortError') {
        setStatus(t('projectsStopped'));
      } else {
        const message = error?.message || 'prompt_generation_failed';
        setStatus(t('promptAiError', { message }), 4000);
      }
    } finally {
      generating = false;
      button.disabled = false;
      roleSelect.disabled = false;
      controller = null;
      console.log('[projects:promptAi:complete]', {
        scope: button.id,
        generating,
      });
    }
  });

  return {
    abort: () => stopGeneration(),
    reset: () => setStatus('—'),
  };
};

const promptAiHandlers = (window.promptAiHandlers = window.promptAiHandlers || []);
let projectsCache = {};
let projectStorageCache = {};
let projectStatusTimer = null;
let lastProjectCount = 0;
let startUrlManual = false;

if (!mainPromptAiHandler) {
  const handler = initPromptAiControls({
    textarea: projectPromptInput,
    domainInput: projectDomainInput,
    roleSelect: projectPromptRoleSelect,
    button: projectPromptAiBtn,
    status: projectPromptAiStatus,
  });
  if (handler) {
    mainPromptAiHandler = handler;
    promptAiHandlers.push(handler);
  }
}

const modalPromptAiHandler = initPromptAiControls({
  textarea: projectModalPrompt,
  domainInput: projectModalDomain,
  roleSelect: projectModalPromptRole,
  button: projectModalPromptAiBtn,
  status: projectModalPromptAiStatus,
});
if (modalPromptAiHandler) {
  promptAiHandlers.push(modalPromptAiHandler);
}

const toggleProjectModalVisibility = (visible) => {
  if (!projectModalBackdrop) return;
  projectModalBackdrop.classList.toggle('show', visible);
  projectModalBackdrop.setAttribute('data-visible', visible ? 'true' : 'false');
  if (document.body) {
    document.body.classList.toggle('modal-open', visible);
  }
  if (!visible) {
    modalPromptAiHandler?.abort?.();
    modalPromptAiHandler?.reset?.();
    if (projectModalStatus) projectModalStatus.textContent = '';
  }
};

const resetProjectModal = () => {
  if (!projectModalForm) return;
  projectModalForm.reset();
  modalPromptAiHandler?.reset?.();
  if (projectModalStatus) projectModalStatus.textContent = '';
  if (projectModalPromptAiStatus) projectModalPromptAiStatus.textContent = '—';
  projectModalName?.classList.remove('input-warning');
};

const openProjectModal = () => {
  resetProjectModal();
  toggleProjectModalVisibility(true);
  projectModalName?.focus();
};

const closeProjectModal = () => {
  toggleProjectModalVisibility(false);
};

const setProjectModalDisabled = (disabled) => {
  if (!projectModalForm) return;
  Array.from(projectModalForm.elements).forEach((element) => {
    element.disabled = disabled;
  });
  if (projectModalClose) {
    projectModalClose.disabled = disabled;
  }
  if (projectModalBackdrop) {
    projectModalBackdrop.setAttribute('data-busy', disabled ? 'true' : 'false');
  }
};

const warnProjectSlugDuplicate = (slug) => {
  if (!projectModalStatus) return;
  const duplicateExists = slug && projectsCache && Object.prototype.hasOwnProperty.call(projectsCache, slug);
  if (duplicateExists) {
    projectModalStatus.textContent = translate('projectsIdentifierExists');
    projectModalName?.classList.add('input-warning');
  } else if (projectModalStatus.textContent === translate('projectsIdentifierExists')) {
    projectModalStatus.textContent = '';
    projectModalName?.classList.remove('input-warning');
  } else {
    projectModalName?.classList.remove('input-warning');
  }
};

if (projectModalName) {
  projectModalName.addEventListener('input', () => {
    if (projectModalBackdrop?.getAttribute('data-busy') === 'true') {
      return;
    }
    const originalValue = projectModalName.value;
    const normalized = safeNormalizeProjectName(originalValue);
    if (originalValue !== normalized) {
      const { selectionStart, selectionEnd } = projectModalName;
      projectModalName.value = normalized;
      if (typeof selectionStart === 'number' && typeof selectionEnd === 'number') {
        projectModalName.setSelectionRange(selectionStart, selectionEnd);
      }
    }
    warnProjectSlugDuplicate(projectModalName.value);
  });
}

const startUrlInput = document.getElementById('url');
if (startUrlInput) {
  startUrlInput.addEventListener('input', () => {
    startUrlManual = true;
  });
}

window.projectsCache = projectsCache;
window.projectStorageCache = projectStorageCache;

function setProjectStatus(message, timeoutMs = 0) {
  if (!projectStatus) return;
  if (projectStatusTimer) {
    clearTimeout(projectStatusTimer);
    projectStatusTimer = null;
  }
  projectStatus.textContent = message || '—';
  if (timeoutMs > 0) {
    const snapshot = projectStatus.textContent;
    projectStatusTimer = setTimeout(() => {
      if (projectStatus && projectStatus.textContent === snapshot) {
        projectStatus.textContent = '—';
      }
      projectStatusTimer = null;
    }, timeoutMs);
  }
}

function updateProjectSummary() {
  if (typeof setSummaryProject !== 'function' || typeof setSummaryPrompt !== 'function') {
    return;
  }
  const normalized = (currentProject || '').trim().toLowerCase();
  const project = normalized ? projectsCache[normalized] || null : null;
  if (!project) {
    setSummaryProject('—', t('overviewProjectMeta'));
    setSummaryPrompt('', [], t('projectsSelectForActivity'));
    return;
  }
  const metaBits = [];
  if (project.domain) metaBits.push(t('projectsDomainLabel', { value: project.domain }));
  if (project.llm_model) metaBits.push(t('projectsModelLabel', { value: project.llm_model }));
  const emoText = project.llm_emotions_enabled === false ? t('projectsEmotionsOff') : t('projectsEmotionsOn');
  metaBits.push(emoText);
  metaBits.push(project.debug_info_enabled ? t('projectsHelpOn') : t('projectsHelpOff'));
  metaBits.push(project.debug_enabled ? t('projectsDebugOn') : t('projectsDebugOff'));
  metaBits.push(project.llm_sources_enabled ? t('projectsSourcesOn') : t('projectsSourcesOff'));
  metaBits.push(
    project.knowledge_image_caption_enabled === false
      ? t('projectsCaptionsOff')
      : t('projectsCaptionsOn'),
  );
  if (project.llm_voice_enabled === false) {
    metaBits.push(t('projectsVoiceModeOff'));
  } else if (project.llm_voice_model) {
    metaBits.push(t('projectsVoiceModelLabel', { value: project.llm_voice_model }));
  } else {
    metaBits.push(t('projectsVoiceModeOn'));
  }
  const storage = projectStorageCache[normalized] || projectStorageCache.__default__ || null;
  if (storage) {
    const textBytes = storage.text_bytes || storage.documents_bytes || 0;
    const fileBytes = storage.binary_bytes || 0;
    const ctxBytes = storage.context_bytes || 0;
    const redisBytes = storage.redis_bytes || 0;
    metaBits.push(
      t('projectsStorageSummary', {
        text: formatBytesOptionalFn(textBytes),
        files: formatBytesOptionalFn(fileBytes),
        contexts: formatBytesOptionalFn(ctxBytes),
        redis: formatBytesOptionalFn(redisBytes),
      }),
    );
  }
  setSummaryProject(
    project.title || project.name || normalized,
    metaBits.join('\n') || '—',
  );
  setSummaryPrompt('', [], t('projectsAwaitingActivity'));
}

function handleProjectsLanguageApplied() {
  renderPromptRoleOptions(projectPromptRoleSelect);
  if (projectModalPromptRole) renderPromptRoleOptions(projectModalPromptRole);
  if (projectAdminPasswordInput) {
    projectAdminPasswordInput.placeholder = adminSession.is_super
      ? t('projectsKeepEmpty')
      : t('projectsPasswordPrompt');
  }
  const currentProjectEntry = currentProject ? projectsCache[currentProject] || null : null;
  updateProjectAdminHintText(currentProjectEntry);
  if (projectEmotionsInput) refreshEmotionsHint(projectEmotionsInput.checked);
  if (projectVoiceInput) refreshVoiceHint(projectVoiceInput.checked);
  if (projectImageCaptionsInput) refreshImageCaptionsHint(projectImageCaptionsInput.checked);
  if (projectSourcesInput) refreshSourcesHint(projectSourcesInput.checked);
  if (projectDebugInfoInput) refreshDebugInfoHint(projectDebugInfoInput.checked);
  if (projectDebugInput) refreshDebugHint(projectDebugInput.checked);
  refreshProjectWidgetUI();
  updateProjectSummary();
  updateProjectDeleteInfo(currentProject);
}

window.ProjectsModule = {
  setProjectStatus,
  updateProjectSummary,
  fetchProjectStorage,
  fetchProjects,
  loadProjectsList,
  populateProjectForm,
  loadLlmModels,
  refreshProjectWidgetUI,
  promptAiHandlers,
  handleLanguageApplied: handleProjectsLanguageApplied,
};

const useIntegration = (name) => {
  const registry = window.ProjectIntegrations || {};
  const integration = registry[name];
  return integration && typeof integration === 'object' ? integration : null;
};

async function loadProjectsList() {
  return Object.keys(projectsCache);
}

async function fetchProjectStorage() {
  try {
    const resp = await fetch('/api/v1/admin/projects/storage', { credentials: 'same-origin' });
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();
    if (data && typeof data === 'object' && data.projects && typeof data.projects === 'object') {
      projectStorageCache = data.projects;
    } else {
      projectStorageCache = {};
    }
    updateProjectDeleteInfo(currentProject);
  } catch (error) {
    console.error('project_storage_fetch_failed', error);
  }
}

function updateProjectDeleteInfo(projectKey) {
  syncProjectDangerZone(projectKey);
  if (!projectDeleteInfo) return;
  if (!projectKey) {
    projectDeleteInfo.textContent = t('projectsSelectForStorage');
    return;
  }
  const stats = projectStorageCache?.[projectKey];
  if (!stats || typeof stats !== 'object') {
    projectDeleteInfo.textContent = t('projectsStorageUnavailable');
    return;
  }
  const docCount = Number.isFinite(stats.document_count) ? Number(stats.document_count) : null;
  const contextCount = Number.isFinite(stats.context_count) ? Number(stats.context_count) : null;
  const redisKeys = Number.isFinite(stats.redis_keys) ? Number(stats.redis_keys) : null;
  const parts = [];
  const textBytes = Number(stats.text_bytes || stats.documents_bytes || 0);
  const fileBytes = Number(stats.binary_bytes || 0);
  const ctxBytes = Number(stats.context_bytes || 0);
  const redisBytes = Number(stats.redis_bytes || 0);
  if (docCount !== null) parts.push(t('projectsDeleteDocuments', { value: docCount }));
  if (contextCount !== null) parts.push(t('projectsDeleteContexts', { value: contextCount }));
  if (redisKeys !== null) parts.push(t('projectsDeleteRedisKeys', { value: redisKeys }));
  parts.push(t('projectsDeleteTextsSize', { value: formatBytesOptionalFn(textBytes) }));
  parts.push(t('projectsDeleteFilesSize', { value: formatBytesOptionalFn(fileBytes) }));
  parts.push(t('projectsDeleteContextsSize', { value: formatBytesOptionalFn(ctxBytes) }));
  parts.push(t('projectsDeleteRedisSize', { value: formatBytesOptionalFn(redisBytes) }));
  projectDeleteInfo.textContent = parts.join(' · ');
}

function updateProjectInputs() {
  if (!projectForm) return;
  const hasProject = Boolean(currentProject && projectsCache[currentProject]);
  const elements = projectForm.querySelectorAll('[data-project-field]');
  elements.forEach((element) => {
    element.disabled = !hasProject;
  });
}

window.fetchProjectStorage = fetchProjectStorage;
window.loadProjectsList = loadProjectsList;

function refreshProjectWidgetUI() {
  if (!projectWidgetUrl || !projectWidgetLink || !projectWidgetHint || !projectWidgetCopyBtn) return;
  const normalized = (currentProject || '').trim().toLowerCase();
  const customValue = projectWidgetUrl.value.trim();
  const defaultPath = getDefaultWidgetPath(normalized);
  const effectivePath = customValue || defaultPath;
  if (!normalized) {
    projectWidgetLink.href = '#';
    projectWidgetLink.textContent = t('projectsOpenWidget');
    projectWidgetLink.style.pointerEvents = 'none';
    projectWidgetLink.style.opacity = '0.6';
    projectWidgetCopyBtn.disabled = true;
    projectWidgetHint.textContent = t('projectsWidgetNoProject');
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
    projectWidgetHint.textContent = customValue
      ? t('projectsWidgetCustomLink')
      : t('projectsWidgetDefault', { path: defaultPath || '/widget' });
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
      if (projectWidgetMessage) projectWidgetMessage.textContent = t('projectsCopied');
    } catch (error) {
      console.error(error);
      if (projectWidgetMessage) projectWidgetMessage.textContent = t('projectsCopyFailed');
    }
    if (projectWidgetMessage) {
      setTimeout(() => { projectWidgetMessage.textContent = ''; }, 2000);
    }
  });
}

const refreshEmotionsHint = (enabled) => {
  if (!projectEmotionsHint) return;
  projectEmotionsHint.textContent = enabled
    ? t('projectsEmotionsOnHint')
    : t('projectsEmotionsOffHint');
};

const refreshVoiceHint = (enabled) => {
  if (!projectVoiceHint) return;
  projectVoiceHint.textContent = enabled
    ? t('projectsWidgetVoiceHintOn')
    : t('projectsWidgetVoiceHintOff');
  if (projectVoiceModelInput) {
    projectVoiceModelInput.disabled = !enabled;
  }
};

const refreshImageCaptionsHint = (enabled) => {
  if (!projectImageCaptionsHint) return;
  projectImageCaptionsHint.textContent = enabled
    ? t('projectsCaptionsHint')
    : t('projectsCaptionsOffHint');
};

const refreshSourcesHint = (enabled) => {
  if (!projectSourcesHint) return;
  projectSourcesHint.textContent = enabled
    ? t('projectsSourcesOnHint')
    : t('projectsSourcesOffHint');
};

const refreshDebugInfoHint = (enabled) => {
  if (!projectDebugInfoHint) return;
  projectDebugInfoHint.textContent = enabled
    ? t('projectsDebugInfoOnHint')
    : t('projectsDebugInfoOffHint');
};

const refreshDebugHint = (enabled) => {
  if (!projectDebugHint) return;
  projectDebugHint.textContent = enabled
    ? t('projectsDebugOnHint')
    : t('projectsDebugOffHint');
};

const updateProjectAdminHintText = (project) => {
  if (!projectAdminHint) return;
  if (!project) {
    projectAdminHint.textContent = t('projectsAdminSelectHint');
  } else if (adminSession.is_super) {
    projectAdminHint.textContent = project?.admin_password_set
      ? t('projectsAdminPasswordSet')
      : t('projectsAdminCredentialsHint');
  } else {
    projectAdminHint.textContent = project?.admin_password_set
      ? t('projectsAdminPasswordChange')
      : t('projectsAdminPasswordSetup');
  }
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
useIntegration('telegram')?.reset?.();
useIntegration('max')?.reset?.();
useIntegration('vk')?.reset?.();
useIntegration('mail')?.reset?.();
useIntegration('bitrix')?.reset?.();

voiceModule?.reset?.();
updateProjectDeleteInfo('');
updateProjectInputs();

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
  projectNameInput.value = project ? project.name : normalized;
  projectNameInput.readOnly = !adminSession.is_super;
  projectTitleInput.value = project?.title || '';
  projectDomainInput.value = project?.domain || '';
  populateModelOptions(project?.llm_model || '');
  projectPromptInput.value = project?.llm_prompt || '';
if (projectPromptRoleSelect) renderPromptRoleOptions(projectPromptRoleSelect);
if (projectModalPromptRole) renderPromptRoleOptions(projectModalPromptRole);
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
  if (projectStorageText) projectStorageText.textContent = storage ? formatBytesOptionalFn(textBytes) : '—';
  if (projectStorageFiles) projectStorageFiles.textContent = storage ? formatBytesOptionalFn(fileBytes) : '—';
  if (projectStorageContexts) projectStorageContexts.textContent = storage ? formatBytesOptionalFn(ctxBytes) : '—';
  if (projectStorageRedis) projectStorageRedis.textContent = storage ? formatBytesOptionalFn(redisBytes) : '—';
  if (projectWidgetUrl) {
    projectWidgetUrl.value = project?.widget_url || '';
  }
  useIntegration('telegram')?.applyProject?.(project);
  useIntegration('max')?.applyProject?.(project);
  useIntegration('vk')?.applyProject?.(project);
  useIntegration('bitrix')?.applyProject?.(project);
  useIntegration('mail')?.applyProject?.(project);
  voiceModule?.refresh?.(project ? project.name : null);
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
      ? t('projectsKeepEmpty')
      : t('projectsPasswordPrompt');
  }
  updateProjectAdminHintText(project);
  if (crawlerProjectLabel) {
    crawlerProjectLabel.textContent = project ? project.name || normalized || '—' : (normalized || '—');
  }
  const metaBits = [];
  if (project?.domain) metaBits.push(t('projectsDomainLabel', { value: project.domain }));
  if (project?.llm_model) metaBits.push(t('projectsModelLabel', { value: project.llm_model }));
  if (project) {
    const emoText = project.llm_emotions_enabled === false ? t('projectsEmotionsOff') : t('projectsEmotionsOn');
    metaBits.push(emoText);
    metaBits.push(project.debug_info_enabled ? t('projectsHelpOn') : t('projectsHelpOff'));
    metaBits.push(project.debug_enabled ? t('projectsDebugOn') : t('projectsDebugOff'));
    metaBits.push(project.llm_sources_enabled ? t('projectsSourcesOn') : t('projectsSourcesOff'));
    metaBits.push(
      project.knowledge_image_caption_enabled === false
        ? t('projectsCaptionsOff')
        : t('projectsCaptionsOn')
    );
    const voiceEnabledBit = project.llm_voice_enabled === false ? t('projectsVoiceModeOff') : t('projectsVoiceModeOn');
    if (project.llm_voice_enabled !== false && project.llm_voice_model) {
      metaBits.push(t('projectsVoiceModelLabel', { value: project.llm_voice_model }));
    } else {
      metaBits.push(voiceEnabledBit);
    }
  }
  if (storage && (textBytes || fileBytes || ctxBytes || redisBytes)) {
    metaBits.push(
      t('projectsStorageSummary', {
        text: formatBytesOptionalFn(textBytes),
        files: formatBytesOptionalFn(fileBytes),
        contexts: formatBytesOptionalFn(ctxBytes),
        redis: formatBytesOptionalFn(redisBytes),
      })
    );
  }
  setSummaryProject(
    project?.title || project?.name || normalized || '—',
    metaBits.join('\n') || t('overviewProjectMeta'),
  );
  setSummaryPrompt('', [], project ? t('projectsAwaitingActivity') : t('projectsSelectForActivity'));
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
  if (typeof window.onAdminProjectChange === 'function') {
    try {
      window.onAdminProjectChange(currentProject);
    } catch (error) {
      console.error('admin_project_change_handler_failed', error);
    }
  }
  projectSelect.value = currentProject;
  updateProjectInputs();
  projectPromptSaveBtn.disabled = !project;
  updateProjectDeleteInfo(currentProject);
  refreshProjectWidgetUI();
  useIntegration('telegram')?.load?.(currentProject);
  useIntegration('max')?.load?.(currentProject);
  useIntegration('vk')?.load?.(currentProject);
  if (typeof loadRequestStats === 'function') {
    loadRequestStats();
  }
  if (currentProject) {
    localStorage.setItem('admin_project', currentProject);
  } else {
    localStorage.removeItem('admin_project');
  }
}

async function fetchProjects(){
  try {
    const resp = await fetch('/api/v1/admin/projects', { credentials: 'same-origin' });
    if (!resp.ok) {
      setProjectStatus(t('projectsLoadFailed'), 3000);
      return;
    }
    const data = await resp.json();
    const projects = Array.isArray(data.projects) ? data.projects : [];
    projectSelect.innerHTML = '';
    projectsCache = {};
    lastProjectCount = projects.length;

    if (!projects.length) {
      const emptyOption = new Option(t('projectsEmptyPlaceholder'), '', true, true);
      emptyOption.dataset.i18n = 'projectsEmptyPlaceholder';
      projectSelect.appendChild(emptyOption);
      projectSelect.disabled = true;
      currentProject = '';
      populateProjectForm('');
      updateProjectSummary();
      projectPromptSaveBtn.disabled = true;
      return;
    }

    const normalizedNames = projects
      .map((project) => safeNormalizeProjectName(project.name))
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
      const placeholderOption = new Option(t('projectsSelectPlaceholder'), '', false, !selectedKey);
      placeholderOption.dataset.i18n = 'projectsSelectPlaceholder';
      projectSelect.appendChild(placeholderOption);
    }

    projects.forEach((p, index) => {
      const key = safeNormalizeProjectName(p.name);
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
    setProjectStatus(t('projectsLoadError'), 3000);
  }
}

projectSelect.addEventListener('change', () => {
  currentProject = projectSelect.value.trim().toLowerCase();
  populateProjectForm(currentProject);
  loadKnowledge(currentProject);
  pollStatus();
});


projectPromptSaveBtn.addEventListener('click', () => {
  if (projectPromptSaveBtn.disabled) return;
  projectForm.requestSubmit();
});

if (projectAddBtn && projectModalBackdrop) {
  projectAddBtn.addEventListener('click', () => {
    if (!adminSession?.can_manage_projects) {
    setProjectStatus(translate('projectsNoPermission'), 3000);
    return;
  }
  openProjectModal();
});
}

if (projectModalCancel) {
  projectModalCancel.addEventListener('click', () => closeProjectModal());
}

if (projectModalClose) {
  projectModalClose.addEventListener('click', () => closeProjectModal());
}

if (projectModalBackdrop) {
  projectModalBackdrop.addEventListener('click', (event) => {
    if (event.target === projectModalBackdrop) {
      closeProjectModal();
    }
  });
}

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && projectModalBackdrop?.classList.contains('show')) {
    closeProjectModal();
  }
});

projectForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const name = projectNameInput.value.trim().toLowerCase();
  if (!name) {
    setProjectStatus(t('projectsEnterIdentifier'), 3000);
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
  setProjectStatus(t('projectsSaving'));
  try {
    const resp = await fetch('/api/v1/admin/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'same-origin',
    });
    if (!resp.ok) {
      setProjectStatus(t('projectsSaveFailed'), 4000);
      return;
    }
    currentProject = name;
    await fetchProjects();
    await loadProjectsList();
    await fetchProjectStorage();
    await loadKnowledge(currentProject);
    pollStatus();
    setProjectStatus(t('projectsSaved'), 2000);
    populateProjectForm(currentProject);
  } catch (error) {
    console.error(error);
    setProjectStatus(t('projectsSaveError'), 4000);
  }
});

if (projectModalForm) {
  projectModalForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!adminSession?.can_manage_projects) {
      if (projectModalStatus) projectModalStatus.textContent = translate('projectsNoPermission');
      return;
    }
    const rawName = projectModalName?.value?.trim() || '';
    const normalizedName = safeNormalizeProjectName(rawName);
    if (!normalizedName) {
      if (projectModalStatus) projectModalStatus.textContent = translate('projectsEnterIdentifier');
      projectModalName?.focus();
      return;
    }
    if (normalizedName && projectsCache && Object.prototype.hasOwnProperty.call(projectsCache, normalizedName)) {
      if (projectModalStatus) projectModalStatus.textContent = translate('projectsIdentifierExists');
      projectModalName?.focus();
      warnProjectSlugDuplicate(normalizedName);
      setProjectModalDisabled(false);
      return;
    }

    const payload = {
      name: normalizedName,
      title: projectModalTitle?.value?.trim() || null,
      domain: projectModalDomain?.value?.trim() || null,
      llm_model: projectModalModel?.value || null,
      llm_prompt: projectModalPrompt?.value?.trim() || null,
      llm_emotions_enabled: projectModalEmotions ? !!projectModalEmotions.checked : true,
    };
    const adminUsername = projectModalAdminUsername?.value?.trim() || '';
    if (adminUsername) {
      payload.admin_username = adminUsername;
    }
    const adminPassword = projectModalAdminPassword?.value || '';
    if (adminPassword.trim()) {
      payload.admin_password = adminPassword;
    }

    if (projectModalStatus) projectModalStatus.textContent = translate('projectsSaving');
    setProjectModalDisabled(true);

    try {
      const resp = await fetch('/api/v1/admin/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'same-origin',
      });
      if (!resp.ok) {
        if (projectModalStatus) projectModalStatus.textContent = translate('projectsSaveFailed');
        return;
      }
      await resp.json().catch(() => ({}));
      currentProject = normalizedName;
      await fetchProjects();
      await loadProjectsList();
      await fetchProjectStorage();
      await loadKnowledge(currentProject);
      pollStatus();
      setProjectStatus(translate('projectsSaved'), 2000);
      closeProjectModal();
    } catch (error) {
      console.error(error);
      if (projectModalStatus) projectModalStatus.textContent = translate('projectsSaveError');
    } finally {
      setProjectModalDisabled(false);
    }
  });
}

if (projectDeleteBtn) projectDeleteBtn.addEventListener('click', async () => {
  if (!currentProject) return;
  if (!confirm(t('projectsDeleteConfirm', { project: currentProject }))) return;
  const toDelete = currentProject;
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(toDelete)}`, { method: 'DELETE', credentials: 'same-origin' });
    if (!resp.ok) {
      setProjectStatus(t('projectsDeleteFailed'), 4000);
      return;
    }
    const payload = await resp.json().catch(() => ({}));
    delete projectsCache[toDelete];
    currentProject = '';
    window.currentProject = '';
    if (typeof window.resetKnowledgeSelection === 'function') {
      window.resetKnowledgeSelection();
    }
    await fetchProjects();
    await loadProjectsList();
    await fetchProjectStorage();
    const legacyTable = document.getElementById('kbTable');
    if (legacyTable) legacyTable.innerHTML = '';
    const kbInfoEl = document.getElementById('kbInfo');
    if (kbInfoEl) kbInfoEl.textContent = '';
    const removed = payload?.removed || {};
    const parts = [];
    if (typeof removed.documents === 'number') parts.push(t('projectsRemovedDocuments', { value: removed.documents }));
    if (typeof removed.files === 'number') parts.push(t('projectsRemovedFiles', { value: removed.files }));
    if (typeof removed.contexts === 'number') parts.push(t('projectsRemovedContexts', { value: removed.contexts }));
    if (typeof removed.stats === 'number') parts.push(t('projectsRemovedStats', { value: removed.stats }));
    setProjectStatus(
      parts.length ? t('projectsRemovedSummary', { value: parts.join(', ') }) : t('projectsDeleted'),
      4000,
    );
    if (typeof window.applySessionPermissions === 'function') {
      window.applySessionPermissions();
    }
    updateProjectDeleteInfo(currentProject);
  } catch (error) {
    console.error(error);
    setProjectStatus(t('projectsDeleteError'), 4000);
  }
});

projectTestBtn.addEventListener('click', async () => {
  if (!currentProject) {
    setProjectStatus(t('projectsSelectProject'), 3000);
    return;
  }
  setProjectStatus(t('projectsTestingServices'));
  try {
    const resp = await fetch(`/api/v1/admin/projects/${encodeURIComponent(currentProject)}/test`, { credentials: 'same-origin' });
    if (!resp.ok) {
      setProjectStatus(t('projectsTestError'), 4000);
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
    setProjectStatus(t('projectsTestError'), 4000);
  }
});
