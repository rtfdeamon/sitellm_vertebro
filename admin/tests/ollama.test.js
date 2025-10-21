import { describe, it, beforeEach, afterEach, expect, vi } from 'vitest';

let activeTranslations;
let translations;
let tStub;

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

    translations = {
      ru: {
        ollamaServerDefaultTitle: 'По умолчанию',
        ollamaServerUnnamed: 'Без названия',
        ollamaServerHealthy: 'healthy',
        ollamaServerStatusTitle: 'Status',
        ollamaLatencyLabel: 'Latency',
        ollamaLatencyValue: '{value} мс',
        ollamaRequestsPerHour: 'Запросов/час',
        ollamaInFlight: 'В работе',
        ollamaServerToggleOn: 'Включён',
        ollamaServerToggleOff: 'Отключён',
        ollamaServersNone: 'Нет серверов.',
        ollamaInstallButton: 'Установить',
        ollamaInstalling: 'Установка…',
        ollamaCatalogSummary: 'Локальная команда Ollama доступна. Установлено моделей: {count}.',
        ollamaCatalogRemoteSummary: 'Доступен удалённый сервер Ollama. Установлено моделей: {count}.',
        ollamaCatalogHybridSummary: 'Доступны оба источника. Установлено моделей: {count}.',
      },
      en: {
        ollamaServerDefaultTitle: 'Default',
        ollamaServerUnnamed: 'Unnamed',
        ollamaServerHealthy: 'healthy',
        ollamaServerStatusTitle: 'Status',
        ollamaLatencyLabel: 'Latency',
        ollamaLatencyValue: '{value} ms',
        ollamaRequestsPerHour: 'Requests/hour',
        ollamaInFlight: 'In flight',
        ollamaServerToggleOn: 'Enabled',
        ollamaServerToggleOff: 'Disabled',
        ollamaServersNone: 'No servers configured.',
        ollamaInstallButton: 'Install',
        ollamaInstalling: 'Installing…',
        ollamaCatalogSummary: 'Local Ollama CLI available. Models installed: {count}.',
        ollamaCatalogRemoteSummary: 'Remote Ollama server available. Models installed: {count}.',
        ollamaCatalogHybridSummary: 'Local CLI and remote servers available. Models installed: {count}.',
      },
    };
    activeTranslations = translations.ru;
    tStub = vi.fn((key, params = {}) => {
      const template = activeTranslations[key] || key;
      return template.replace(/\{(\w+)\}/g, (_, token) => {
        if (Object.prototype.hasOwnProperty.call(params, token)) {
          return String(params[token]);
        }
        return '';
      });
    });

    vi.stubGlobal('t', tStub);

    vi.stubGlobal('fetch', vi.fn((url) => {
      if (url === '/api/v1/admin/ollama/servers') {
        return Promise.resolve({
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
        });
      }
      if (url === '/api/v1/admin/ollama/catalog') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            available: false,
            cli_available: false,
            remote_available: false,
            installed: [],
            popular: [],
            jobs: {},
          }),
        });
      }
      throw new Error(`Unexpected fetch URL ${url}`);
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

  it('перерисовывает элементы каталога и серверов при смене языка', async () => {
    fetch.mockImplementation((url) => {
      if (url === '/api/v1/admin/ollama/servers') {
        return Promise.resolve({
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
        });
      }
      if (url === '/api/v1/admin/ollama/catalog') {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            available: false,
            cli_available: false,
            remote_available: false,
            installed: [],
            popular: [
              {
                name: 'yandex/model',
                approx_size_human: '4 GB',
                installed: false,
              },
            ],
            jobs: {},
          }),
        });
      }
      throw new Error(`Unexpected fetch URL ${url}`);
    });

    await import('../js/ollama.js');
    await window.refreshOllamaServers();
    await window.refreshOllamaCatalog();

    let toggleLabel = document.querySelector('.ollama-server-toggle span');
    expect(toggleLabel?.textContent).toBe('Включён');
    let installButton = document.querySelector('.ollama-install-btn');
    expect(installButton?.textContent).toBe('Установить');

    activeTranslations = translations.en;
    await window.OllamaModule.handleLanguageApplied();

    toggleLabel = document.querySelector('.ollama-server-toggle span');
    expect(toggleLabel?.textContent).toBe('Enabled');
    installButton = document.querySelector('.ollama-install-btn');
    expect(installButton?.textContent).toBe('Install');
  });
});
