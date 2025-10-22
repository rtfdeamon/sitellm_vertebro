import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const setupDom = () => {
  document.body.innerHTML = `
    <div>
      <div class="kb-section-nav">
        <button id="kbTabOverview" data-kb-target="overview" class="kb-tab-button active" aria-selected="true"></button>
        <button id="kbTabDocuments" data-kb-target="documents" class="kb-tab-button" aria-selected="false"></button>
        <button id="kbTabUnanswered" data-kb-target="unanswered" class="kb-tab-button" aria-selected="false"></button>
      </div>
      <div id="kbSectionOverview" data-kb-section="overview" class="kb-section active" aria-hidden="false">
        <span id="kbInfo"></span>
        <span id="kbProjectsSummary"></span>
      </div>
      <div id="kbSectionDocuments" data-kb-section="documents" class="kb-section" aria-hidden="true">
        <div class="kb-category" data-kb-category="text">
          <span id="kbCountText">—</span>
          <div class="kb-table-wrapper">
            <table><tbody id="kbTableText"></tbody></table>
          </div>
        </div>
        <div class="kb-category" data-kb-category="docs">
          <span id="kbCountDocs">—</span>
          <div class="kb-table-wrapper">
            <table><tbody id="kbTableDocs"></tbody></table>
          </div>
        </div>
        <div class="kb-category" data-kb-category="images">
          <span id="kbCountImages">—</span>
          <div class="kb-table-wrapper">
            <table><tbody id="kbTableImages"></tbody></table>
          </div>
        </div>
      </div>
      <div id="kbSectionUnanswered" data-kb-section="unanswered" class="kb-section" aria-hidden="true">
        <span id="kbCountUnanswered">—</span>
        <div class="kb-table-wrapper">
          <table class="unanswered-table"><tbody id="kbTableUnanswered"></tbody></table>
        </div>
        <button id="kbUnansweredExport"></button>
        <button id="kbUnansweredClear"></button>
        <span id="kbUnansweredStatus"></span>
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
    requestAdminAuth: vi.fn(),
  })));
  vi.stubGlobal('bootstrapAdminApp', vi.fn());
  vi.stubGlobal('deleteKnowledgeDocument', vi.fn());
  vi.stubGlobal('openKnowledgeModal', vi.fn());
  vi.stubGlobal('confirm', vi.fn(() => true));
  vi.stubGlobal('window', globalThis);
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

const documentsResponse = {
  documents: [
    {
      fileId: 'text-1',
      name: 'readme.txt',
      description: 'Text document',
      content_type: 'text/plain',
      project: 'demo',
    },
    null,
    {
      fileId: 'file-1',
      name: 'report.pdf',
      description: 'PDF report',
      content_type: 'application/pdf',
      project: 'demo',
    },
    {
      fileId: 'img-1',
      name: 'photo.png',
      description: 'Image file',
      content_type: 'image/png',
      project: 'demo',
    },
  ],
  total: 3,
  matched: 3,
  has_more: false,
  project: 'demo',
};

const emptyDocumentsResponse = {
  documents: [],
  total: 0,
  matched: 0,
  has_more: false,
  project: 'demo',
};

const mockFetchSequence = (responses) => {
  let callIndex = 0;
  return vi.fn((url) => {
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
    if (typeof url === 'string' && url.includes('/api/v1/admin/logs')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ lines: [] }),
      });
    }
    if (callIndex >= responses.length) {
      throw new Error(`Unexpected fetch URL ${url}`);
    }
    const response = responses[callIndex];
    callIndex += 1;
    if (typeof response === 'function') {
      return response(url);
    }
    return Promise.resolve(response(url));
  });
};

const unanswered404 = () => Promise.resolve({ status: 404 });

describe('Knowledge documents rendering', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    setupDom();
    installGlobalStubs();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('renders documents grouped by category with counters', async () => {
    const fetchMock = mockFetchSequence([
      unanswered404,
      () => Promise.resolve({
        ok: true,
        json: async () => documentsResponse,
      }),
    ]);
    vi.stubGlobal('fetch', fetchMock);

    await import('../js/index.js');
    const bootConfig = globalThis.bootstrapAdminApp.mock.calls[0][0];
    await bootConfig.loadKnowledge('demo');

    await vi.waitFor(() => {
      const relevantCalls = fetchMock.mock.calls.filter(([requestUrl]) => {
        if (typeof requestUrl !== 'string') return true;
        return !requestUrl.includes('/api/v1/llm/info') && !requestUrl.includes('/api/v1/admin/logs');
      });
      expect(relevantCalls).toHaveLength(2);
    });

    expect(document.querySelectorAll('#kbTableText tr')).toHaveLength(1);
    expect(document.querySelectorAll('#kbTableDocs tr')).toHaveLength(1);
    expect(document.querySelectorAll('#kbTableImages tr')).toHaveLength(1);
    expect(document.getElementById('kbCountText').textContent).toBe('1');
    expect(document.getElementById('kbCountDocs').textContent).toBe('1');
    expect(document.getElementById('kbCountImages').textContent).toBe('1');
    expect(document.getElementById('kbInfo').textContent).toBe('knowledgeTotalDocs:3 · knowledgeMatchedDocs:3');
    expect(document.getElementById('kbProjectsSummary').textContent).toBe('knowledgeProjectSummary:demo');
  });

  it('renders placeholders when load fails', async () => {
    const fetchMock = mockFetchSequence([
      unanswered404,
      () => Promise.resolve({
        ok: false,
        status: 500,
      }),
    ]);
    vi.stubGlobal('fetch', fetchMock);

    await import('../js/index.js');
    const bootConfig = globalThis.bootstrapAdminApp.mock.calls[0][0];
    await bootConfig.loadKnowledge('demo');

    await vi.waitFor(() => {
      const relevantCalls = fetchMock.mock.calls.filter(([requestUrl]) => {
        if (typeof requestUrl !== 'string') return true;
        return !requestUrl.includes('/api/v1/llm/info') && !requestUrl.includes('/api/v1/admin/logs');
      });
      expect(relevantCalls).toHaveLength(2);
    });

    const placeholders = Array.from(document.querySelectorAll('#kbSectionDocuments tbody tr td'))
      .map((cell) => cell.textContent);
    expect(placeholders).toContain('knowledgeTableTextEmpty');
    expect(placeholders).toContain('knowledgeTableDocsEmpty');
    expect(placeholders).toContain('knowledgeTableImagesEmpty');
    expect(document.getElementById('kbInfo').textContent).toBe('knowledgeLoadError');
  });
});
