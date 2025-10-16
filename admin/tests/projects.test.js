import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const flushPromises = async () => {
  await Promise.resolve();
  await Promise.resolve();
};

const setupDom = () => {
  const created = new Map();

  const ensure = (id, tag, parentId, options = {}) => {
    if (created.has(id)) return created.get(id);
    const parent = parentId ? created.get(parentId) : document.body;
    if (!parent) {
      throw new Error(`Parent ${parentId} not created for ${id}`);
    }
    const element = document.createElement(tag);
    element.id = id;
    if (options.type) element.type = options.type;
    if (options.text !== undefined) element.textContent = options.text;
    if (options.value !== undefined) element.value = options.value;
    if (options.checked !== undefined) element.checked = options.checked;
    if (options.display !== undefined) element.style.display = options.display;
    parent.appendChild(element);
    created.set(id, element);
    return element;
  };

  // Containers
  ensure('projectForm', 'form');
  ensure('projectModalForm', 'form');

  // Primary project controls
  ensure('projectSelect', 'select');
  ensure('projectStatus', 'span');
  ensure('projectAdd', 'button', null, { type: 'button' });
  ensure('projectRefresh', 'button', null, { type: 'button' });
  ensure('projectPromptSave', 'button', null, { type: 'button' });
  ensure('projectTest', 'button', null, { type: 'button' });
  ensure('projectPrompt', 'textarea', 'projectForm');
  ensure('projectPromptRole', 'select', 'projectForm');
  ensure('projectPromptAi', 'button', 'projectForm', { type: 'button' });
  ensure('projectPromptAiStatus', 'span', 'projectForm', { text: '—' });
  ensure('projectName', 'input', 'projectForm');
  ensure('projectTitle', 'input', 'projectForm');
  ensure('projectDomain', 'input', 'projectForm');
  ensure('projectModel', 'select', 'projectForm');
  ensure('projectWidgetUrl', 'input', 'projectForm');
  ensure('projectWidgetHint', 'span', 'projectForm');
  ensure('projectWidgetLink', 'a', 'projectForm');
  ensure('projectWidgetCopy', 'button', 'projectForm', { type: 'button' });
  ensure('projectWidgetMessage', 'span', 'projectForm');
  ensure('projectEmotions', 'input', 'projectForm', { type: 'checkbox', checked: true });
  ensure('projectEmotionsHint', 'span', 'projectForm');
  ensure('projectVoiceEnabled', 'input', 'projectForm', { type: 'checkbox', checked: true });
  ensure('projectVoiceHint', 'span', 'projectForm');
  ensure('projectVoiceModel', 'input', 'projectForm');
  ensure('projectImageCaptions', 'input', 'projectForm', { type: 'checkbox', checked: true });
  ensure('projectImageCaptionsHint', 'span', 'projectForm');
  ensure('projectSourcesEnabled', 'input', 'projectForm', { type: 'checkbox' });
  ensure('projectSourcesHint', 'span', 'projectForm');
  ensure('projectDebugInfo', 'input', 'projectForm', { type: 'checkbox', checked: true });
  ensure('projectDebugInfoHint', 'span', 'projectForm');
  ensure('projectDebug', 'input', 'projectForm', { type: 'checkbox' });
  ensure('projectDebugHint', 'span', 'projectForm');
  ensure('projectDelete', 'button', 'projectForm', { type: 'button' });
  ensure('projectDeleteInfo', 'span', 'projectForm');
  ensure('projectAdminSection', 'div', 'projectForm', { display: 'flex' });
  ensure('projectAdminUsername', 'input', 'projectForm');
  ensure('projectAdminPassword', 'input', 'projectForm');
  ensure('projectAdminHint', 'span', 'projectForm');
  ensure('projectStorageText', 'span', 'projectForm');
  ensure('projectStorageFiles', 'span', 'projectForm');
  ensure('projectStorageContexts', 'span', 'projectForm');
  ensure('projectStorageRedis', 'span', 'projectForm');
  ensure('projectBitrixEnabled', 'input', 'projectForm', { type: 'checkbox' });
  ensure('projectBitrixWebhook', 'input', 'projectForm');
  ensure('projectBitrixHint', 'span', 'projectForm');
  ensure('projectMailEnabled', 'input', 'projectForm', { type: 'checkbox' });
  ensure('projectMailHint', 'span', 'projectForm');
  ensure('projectMailImapHost', 'input', 'projectForm');
  ensure('projectMailImapPort', 'input', 'projectForm');
  ensure('projectMailImapSsl', 'input', 'projectForm', { type: 'checkbox', checked: true });
  ensure('projectMailSmtpHost', 'input', 'projectForm');
  ensure('projectMailSmtpPort', 'input', 'projectForm');
  ensure('projectMailSmtpTls', 'input', 'projectForm', { type: 'checkbox', checked: true });
  ensure('projectMailUsername', 'input', 'projectForm');
  ensure('projectMailPassword', 'input', 'projectForm');
  ensure('projectMailFrom', 'input', 'projectForm');
  ensure('projectMailSignature', 'textarea', 'projectForm');
  ensure('projectWidgetModalInput', 'input', 'projectForm');
  ensure('crawlerProject', 'span', 'projectForm');
  ensure('projectWidgetModal', 'div');

  // Modal controls
  ensure('projectModalPrompt', 'textarea', 'projectModalForm');
  ensure('projectModalPromptRole', 'select', 'projectModalForm');
  ensure('projectModalPromptAi', 'button', 'projectModalForm', { type: 'button' });
  ensure('projectModalPromptAiStatus', 'span', 'projectModalForm', { text: '—' });
  ensure('projectModalName', 'input', 'projectModalForm');
  ensure('projectModalTitle', 'input', 'projectModalForm');
  ensure('projectModalDomain', 'input', 'projectModalForm');
  ensure('projectModalModel', 'select', 'projectModalForm');
  ensure('projectModalEmotions', 'input', 'projectModalForm', { type: 'checkbox' });
  ensure('projectModalAdminUsername', 'input', 'projectModalForm');
  ensure('projectModalAdminPassword', 'input', 'projectModalForm');

  // Auxiliary holders referenced in code
  ensure('projectDangerZone', 'div');
  ensure('projectVoiceModelOptions', 'datalist');
  ensure('kbTable', 'div');
  ensure('kbInfo', 'div');
  ensure('projectModalPromptRole', 'select', 'projectModalForm');

  return created;
};

const loadProjectsModule = async () => {
  await import('../js/projects.js');
};

describe('Project prompt AI controls', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    setupDom();

    vi.stubGlobal('t', vi.fn((key, params) => {
      if (params && typeof params.message === 'string') {
        return `${key}:${params.message}`;
      }
      if (params && typeof params.value !== 'undefined') {
        return `${key}:${params.value}`;
      }
      return key;
    }));
    vi.stubGlobal('adminSession', { is_super: true, primary_project: null, can_manage_projects: true });
    vi.stubGlobal('currentProject', '');
    vi.stubGlobal('setSummaryProject', vi.fn());
    vi.stubGlobal('setSummaryPrompt', vi.fn());
    vi.stubGlobal('updateProjectAdminHintText', vi.fn());
    vi.stubGlobal('UIUtils', {});
    vi.stubGlobal('VoiceModule', { reset: vi.fn(), refresh: vi.fn() });
    vi.stubGlobal('ProjectIntegrations', {});
    vi.stubGlobal('applySessionPermissions', vi.fn());
    vi.stubGlobal('normalizeProjectName', (value) => (typeof value === 'string' ? value.trim().toLowerCase() : ''));
    vi.stubGlobal('loadKnowledge', vi.fn());
    vi.stubGlobal('pollStatus', vi.fn());
    vi.stubGlobal('loadLlmModels', vi.fn());
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('регистрирует обработчики генерации для основного блока и модального окна', async () => {
    await loadProjectsModule();
    const handlers = window.promptAiHandlers || [];
    expect(handlers).toHaveLength(2);
    expect(handlers[0]).not.toBe(handlers[1]);
    handlers.forEach((handler) => {
      expect(typeof handler.abort).toBe('function');
      expect(typeof handler.reset).toBe('function');
    });
    const roleSelect = document.getElementById('projectPromptRole');
    expect(roleSelect.options.length).toBeGreaterThan(0);
    expect(roleSelect.value).toBe('friendly_expert');
  });

  it('отправляет запрос на генерацию и обновляет текст и статус', async () => {
    vi.useFakeTimers();
    const promptTextarea = document.getElementById('projectPrompt');
    const domainInput = document.getElementById('projectDomain');
    const roleSelect = document.getElementById('projectPromptRole');
    const statusSpan = document.getElementById('projectPromptAiStatus');
    const button = document.getElementById('projectPromptAi');

    domainInput.value = 'mmvs.ru';

    await loadProjectsModule();
    roleSelect.value = roleSelect.options[0].value;

    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ prompt: 'Сгенерированный промпт' }),
    });

    button.click();
    await flushPromises();

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe('/api/v1/admin/projects/prompt');
    expect(init.method).toBe('POST');
    const payload = JSON.parse(init.body);
    expect(payload).toEqual({ url: 'https://mmvs.ru/', role: roleSelect.value });

    await vi.waitFor(() => {
      expect(promptTextarea.value).toBe('Сгенерированный промпт');
      expect(statusSpan.textContent).toBe('promptAiReady');
      expect(button.disabled).toBe(false);
      expect(roleSelect.disabled).toBe(false);
    });

    vi.advanceTimersByTime(2000);
    expect(statusSpan.textContent).toBe('—');
  });

  it('оставляет поле домена доступным для редактирования', async () => {
    await loadProjectsModule();
    const domainInput = document.getElementById('projectDomain');
    expect(domainInput).toBeInstanceOf(HTMLInputElement);
    expect(domainInput.disabled).toBe(false);
    expect(domainInput.readOnly).toBe(false);
    domainInput.value = 'https://example.com';
    expect(domainInput.value).toBe('https://example.com');
  });
});
