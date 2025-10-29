import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const createBaseDom = () => {
  document.body.innerHTML = `
    <div>
      <div class="kb-section-nav">
        <button id="kbTabOverview" data-kb-target="overview" class="kb-tab-button active" aria-selected="true"></button>
        <button id="kbTabUpload" data-kb-target="upload" class="kb-tab-button" aria-selected="false"></button>
        <button id="kbTabDocuments" data-kb-target="documents" class="kb-tab-button" aria-selected="false"></button>
        <button id="kbTabQA" data-kb-target="qa" class="kb-tab-button" aria-selected="false"></button>
        <button id="kbTabUnanswered" data-kb-target="unanswered" class="kb-tab-button" aria-selected="false"></button>
      </div>
      <div id="kbSectionOverview" data-kb-section="overview" class="kb-section active" aria-hidden="false"></div>
      <div id="kbSectionUpload" data-kb-section="upload" class="kb-section" aria-hidden="true"></div>
      <div id="kbSectionDocuments" data-kb-section="documents" class="kb-section" aria-hidden="true"></div>
      <div id="kbSectionQA" data-kb-section="qa" class="kb-section" aria-hidden="true"></div>
      <div id="kbSectionUnanswered" data-kb-section="unanswered" class="kb-section" aria-hidden="true">
        <div class="kb-meta-line">
          <span id="kbCountUnanswered">—</span>
        </div>
        <div class="unanswered-actions">
          <button type="button" id="kbUnansweredExport">export</button>
          <button type="button" id="kbUnansweredClear">clear</button>
          <span id="kbUnansweredStatus"></span>
        </div>
        <table class="unanswered-table">
          <tbody id="kbTableUnanswered"></tbody>
        </table>
      </div>
    </div>
    <button id="saveLLM"></button>
    <button id="pingLLM"></button>
    <input id="ollamaBase" value="">
    <input id="ollamaModel" value="">
    <div id="pingRes"></div>
    <button id="copyLogs"></button>
    <pre id="logs"></pre>
    <span id="logInfo"></span>
  `;
};

const installGlobalStubs = () => {
  const tStub = vi.fn((key, params) => {
    if (params && Object.prototype.hasOwnProperty.call(params, 'value')) {
      return `${key}:${params.value}`;
    }
    return key;
  });
  vi.stubGlobal('initAdminI18n', vi.fn(() => ({
    t: tStub,
    applyLanguage: vi.fn(),
    getCurrentLanguage: vi.fn(() => 'ru'),
  })));
  vi.stubGlobal('t', tStub);
  vi.stubGlobal('applyLanguage', vi.fn());
  vi.stubGlobal('getCurrentLanguage', vi.fn(() => 'ru'));
  vi.stubGlobal('UIUtils', {
    formatTimestamp: () => 'TS',
    formatBytes: () => '0 B',
    formatBytesOptional: () => '—',
    pulseCard: vi.fn(),
  });
  vi.stubGlobal('adminSession', { is_super: true, can_manage_projects: true });
  vi.stubGlobal('currentProject', 'demo');
  vi.stubGlobal('initAdminAuth', vi.fn(() => ({
    clearAuthHeaderForBase: vi.fn(),
    setStoredAdminUser: vi.fn(),
    requestAdminAuth: vi.fn().mockResolvedValue(true),
    getAuthHeaderForBase: vi.fn(() => 'Basic test'),
  })));
  vi.stubGlobal('AdminAuth', {
    getAuthHeaderForBase: vi.fn(() => 'Basic test'),
  });
  vi.stubGlobal('bootstrapAdminApp', vi.fn(() => Promise.resolve()));
  vi.stubGlobal('window', globalThis);
  vi.stubGlobal('confirm', vi.fn(() => true));
  [
    'loadLlmModels',
    'refreshOllamaCatalog',
    'refreshOllamaServers',
    'fetchProjectStorage',
    'fetchProjects',
    'loadProjectsList',
    'loadRequestStats',
    'fetchKnowledgeServiceStatus',
    'fetchFeedbackTasks',
    'populateProjectForm',
    'updateProjectSummary',
  ].forEach((name) => {
    if (!Object.prototype.hasOwnProperty.call(globalThis, name)) {
      vi.stubGlobal(name, vi.fn());
    } else {
      globalThis[name] = vi.fn();
    }
  });
};

describe('Knowledge unanswered tab', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    createBaseDom();
    installGlobalStubs();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('shows unanswered tab when data is returned', async () => {
    const fetchMock = vi.fn((url) => {
      if (url.includes('/api/v1/llm/info')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            model: null,
            backend: 'local',
            device: 'cpu',
            ollama_base: null,
          }),
        });
      }
      if (url.startsWith('/api/v1/admin/knowledge/unanswered')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            items: [
              { question: 'Q1', count: 3, updated_at: 1_700_000_000 },
            ],
          }),
        });
      }
      if (url.startsWith('/api/v1/admin/knowledge')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ documents: [] }),
        });
      }
      throw new Error(`Unexpected fetch URL ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await import('../js/index.js');
    const bootConfig = globalThis.bootstrapAdminApp.mock.calls[0][0];
    await bootConfig.loadKnowledge('demo');

    await vi.waitFor(() => {
      const urls = fetchMock.mock.calls.map(([url]) => url);
      expect(urls).toContain('/api/v1/admin/knowledge/unanswered?project=demo');
    });

    const tab = document.getElementById('kbTabUnanswered');
    const section = document.getElementById('kbSectionUnanswered');
    expect(tab.style.display).not.toBe('none');
    expect(section.style.display).not.toBe('none');
    expect(document.querySelectorAll('#kbTableUnanswered tr')).toHaveLength(1);
    expect(document.getElementById('kbCountUnanswered').textContent).toBe('1');
  });

  it('hides unanswered tab when list is empty', async () => {
    const fetchMock = vi.fn((url) => {
      if (url.includes('/api/v1/llm/info')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            model: null,
            backend: 'local',
            device: 'cpu',
            ollama_base: null,
          }),
        });
      }
      if (url.startsWith('/api/v1/admin/knowledge/unanswered')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ items: [] }),
        });
      }
      if (url.startsWith('/api/v1/admin/knowledge')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ documents: [] }),
        });
      }
      throw new Error(`Unexpected fetch URL ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    await import('../js/index.js');
    const bootConfig = globalThis.bootstrapAdminApp.mock.calls[0][0];
    await bootConfig.loadKnowledge('demo');

    await vi.waitFor(() => {
      const tab = document.getElementById('kbTabUnanswered');
      expect(tab.style.display).toBe('none');
    });
    expect(document.getElementById('kbCountUnanswered').textContent).toBe('—');
    expect(document.querySelectorAll('#kbTableUnanswered tr')).toHaveLength(0);
  });

  it('clears unanswered list and refreshes data', async () => {
    let unansweredCall = 0;
    const fetchMock = vi.fn((url, init = {}) => {
      if (typeof url === 'string' && url.includes('/api/v1/llm/info')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            model: null,
            backend: 'local',
            device: 'cpu',
            ollama_base: null,
          }),
        });
      }
      if (url.startsWith('/api/v1/admin/knowledge/unanswered/clear')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ removed: 2 }),
        });
      }
      if (url.startsWith('/api/v1/admin/knowledge/unanswered')) {
        unansweredCall += 1;
        const hasItems = unansweredCall === 1;
        return Promise.resolve({
          ok: true,
          json: async () => ({
            items: hasItems
              ? [{ question: 'Q', count: 1, updated_at: 1_700_000_000 }]
              : [],
          }),
        });
      }
      if (url.startsWith('/api/v1/admin/knowledge')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ documents: [] }),
        });
      }
      throw new Error(`Unexpected fetch URL ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    await import('../js/index.js');
    const bootConfig = globalThis.bootstrapAdminApp.mock.calls[0][0];
    await bootConfig.loadKnowledge('demo');

    await vi.waitFor(() => {
      expect(document.querySelectorAll('#kbTableUnanswered tr')).toHaveLength(1);
    });

    document.getElementById('kbUnansweredClear').click();
    expect(document.getElementById('kbUnansweredStatus').textContent).toBe('knowledgeUnansweredClearing');

    await vi.waitFor(() => {
      const urls = fetchMock.mock.calls.map(([url]) => url);
      expect(urls).toContain('/api/v1/admin/knowledge/unanswered/clear');
    });

    expect(confirmSpy).toHaveBeenCalled();

    await vi.waitFor(() => {
      expect(document.getElementById('kbTabUnanswered').style.display).toBe('none');
      expect(document.getElementById('kbUnansweredStatus').textContent).toBe('');
      expect(document.querySelectorAll('#kbTableUnanswered tr')).toHaveLength(0);
    });
  });
});
