import { describe, it, beforeEach, afterEach, expect, vi } from 'vitest';

const setupDom = () => {
  document.body.innerHTML = `
    <div id="ollamaCatalog">
      <div id="ollamaAvailability"></div>
      <ul id="ollamaInstalledList"></ul>
      <ul id="ollamaPopularList"></ul>
      <div id="ollamaJobsList"></div>
    </div>
    <div id="ollamaServersPanel">
      <div id="ollamaServersStatus"></div>
      <button id="ollamaServersRefresh" type="button"></button>
      <ul id="ollamaServersList"></ul>
    </div>
    <form id="ollamaServerForm">
      <input id="ollamaServerName" type="text">
      <input id="ollamaServerUrl" type="text">
      <input id="ollamaServerEnabled" type="checkbox" checked>
    </form>
  `;
};

describe('Ollama servers rendering', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    setupDom();

    vi.stubGlobal('t', vi.fn((key, params = {}) => {
      const translations = {
        ollamaServerDefaultTitle: 'По умолчанию',
        ollamaServerUnnamed: 'Без названия',
        ollamaServerHealthy: 'healthy',
        ollamaServerStatusTitle: 'Status',
        ollamaLatencyLabel: 'Latency',
        ollamaLatencyValue: '{value} ms',
        ollamaRequestsPerHour: 'Requests/hour',
        ollamaInFlight: 'In flight',
        ollamaServerToggleOn: 'Enabled',
        ollamaServerToggleOff: 'Disabled',
        ollamaServersNone: 'No servers configured.',
      };
      const template = translations[key] || key;
      return template.replace(/\{(\w+)\}/g, (_, token) => {
        if (Object.prototype.hasOwnProperty.call(params, token)) {
          return String(params[token]);
        }
        return '';
      });
    }));

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        servers: [
          {
            name: 'default',
            base_url: 'http://host.docker.internal:11434',
            enabled: true,
            healthy: true,
            avg_latency_ms: 1800,
            requests_last_hour: 0,
            inflight: 0,
          },
        ],
      }),
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('переводит имя сервера default на русский', async () => {
    await import('../js/ollama.js');
    await window.refreshOllamaServers();

    expect(fetch).toHaveBeenCalledWith('/api/v1/admin/ollama/servers');
    const header = document.querySelector('#ollamaServersList h4');
    expect(header).toBeTruthy();
    expect(header.textContent).toBe('По умолчанию');
  });
});
