import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const defaultDataset = {
  baseUrl: 'https://example.com',
  project: 'demo',
  variant: 'floating',
  color: '#4f7cff',
  position: 'bottom-right',
  title: 'AI Helper',
  subtitle: 'Ask anything',
  icon: 'AI',
  width: '380px',
  height: '640px'
};

const mountLoader = async (dataset = {}, options = {}) => {
  vi.resetModules();
  document.head.innerHTML = '';
  document.body.innerHTML = '';
  const script = document.createElement('script');
  const finalDataset = { ...defaultDataset, ...dataset };
  if (options.omitBaseUrl) {
    delete finalDataset.baseUrl;
  }
  for (const [key, value] of Object.entries(finalDataset)) {
    if (value !== undefined) {
      script.dataset[key] = value;
    }
  }
  script.src = options.scriptSrc || 'https://cdn.example.com/embed/widget-loader.js';
  document.body.appendChild(script);

  Object.defineProperty(document, 'currentScript', {
    configurable: true,
    get: () => script
  });

  await import('../widget-loader.js');
  delete document.currentScript;
};

describe('widget-loader', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('создаёт плавающий виджет с корректным src и стилями', async () => {
    await mountLoader();
    const launcher = document.querySelector('.sitellm-widget-launcher');
    const frame = document.querySelector('.sitellm-widget-frame');
    const overlay = document.querySelector('.sitellm-widget-overlay');
    const iframe = frame?.querySelector('iframe');

    expect(window.SiteLLMWidgetLoader.version).toBe('1.0.0');
    expect(launcher).not.toBeNull();
    expect(frame).not.toBeNull();
    expect(frame?.style.width).toBe(defaultDataset.width);
    expect(frame?.style.height).toBe(defaultDataset.height);
    expect(iframe?.src).toContain('https://example.com/widget/index.html');
    expect(iframe?.src).toContain('project=demo');
    expect(new URL(iframe.src).searchParams.get('v')).toBe('20241010.02');
    expect(overlay).not.toBeNull();
    expect(document.getElementById('__sitellmWidgetStyles')).not.toBeNull();
    launcher?.dispatchEvent(new Event('click'));
    expect(frame?.classList.contains('is-open')).toBe(true);
    expect(overlay?.classList.contains('is-open')).toBe(true);
    overlay?.dispatchEvent(new Event('click'));
    expect(frame?.classList.contains('is-open')).toBe(false);
    expect(overlay?.classList.contains('is-open')).toBe(false);
  });

  it('поддерживает inline-вариант и не создаёт плавающий лаунчер', async () => {
    await mountLoader({ variant: 'inline', width: '600px', height: '500px' });
    const card = document.querySelector('.sitellm-inline-card');
    const launcher = document.querySelector('.sitellm-widget-launcher');
    expect(card).not.toBeNull();
    expect(launcher).toBeNull();
    const iframe = card?.querySelector('iframe');
    expect(iframe?.src).toContain('https://example.com/widget/index.html');
    expect(new URL(iframe.src).searchParams.get('v')).toBe('20241010.02');
  });

  it('не дублирует стили при повторной инициализации', async () => {
    await mountLoader();
    await mountLoader();
    const styles = document.querySelectorAll('#__sitellmWidgetStyles');
    expect(styles.length).toBe(1);
  });

  it('повторно использует сессию для одного проекта', async () => {
    const sessionId = 'session-123';
    vi.spyOn(window.crypto, 'randomUUID').mockReturnValue(sessionId);
    await mountLoader();
    const firstIframe = document.querySelector('.sitellm-widget-frame iframe');
    const firstUrl = new URL(firstIframe.src);
    expect(firstUrl.searchParams.get('session')).toBe(sessionId);

    await mountLoader();
    const secondIframe = document.querySelector('.sitellm-widget-frame iframe');
    const secondUrl = new URL(secondIframe.src);
    expect(secondUrl.searchParams.get('session')).toBe(sessionId);
  });

  it('определяет базовый адрес по src скрипта, если data-base-url отсутствует', async () => {
    await mountLoader({ project: 'beta' }, { omitBaseUrl: true, scriptSrc: 'https://cdn.example.org/assets/widget-loader.js' });
    const iframe = document.querySelector('.sitellm-widget-frame iframe');
    expect(iframe?.src).toContain('https://cdn.example.org/widget/index.html');
    expect(iframe?.src).toContain('project=beta');
  });

  it('прокидывает режим чтения и тему в параметры iframe', async () => {
    await mountLoader({
      readingMode: '1',
      theme: 'dark',
      debug: '1',
    });
    const iframe = document.querySelector('.sitellm-widget-frame iframe');
    const params = new URL(iframe.src).searchParams;
    expect(params.get('reading')).toBe('1');
    expect(params.get('theme')).toBe('dark');
    expect(params.get('debug')).toBe('1');
  });
});
