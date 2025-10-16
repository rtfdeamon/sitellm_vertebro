import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('Static i18n fallbacks', () => {
  let api;

  beforeEach(async () => {
    vi.resetModules();
    vi.stubGlobal('localStorage', {
      storage: {},
      getItem(key) {
        return this.storage[key] || null;
      },
      setItem(key, value) {
        this.storage[key] = value;
      },
      removeItem(key) {
        delete this.storage[key];
      },
      clear() {
        this.storage = {};
      },
    });
    const fakeDocument = {
      documentElement: { lang: 'en', dir: 'ltr' },
      getElementById: () => null,
      querySelectorAll: () => [],
    };
    vi.stubGlobal('document', fakeDocument);
    vi.stubGlobal('window', { document: fakeDocument, location: { origin: 'https://example.com' } });
    await import('../js/i18n-static.js');
    const module = await import('../js/i18n.js');
    api = window.initAdminI18n({});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('возвращает английский текст для статических ключей', () => {
    api.applyLanguage('en');
    expect(api.t('projectsRoleFriendlyLabel')).toBe('Friendly expert');
    expect(api.t('summaryCrawlerTitle')).toBe('Crawling');
    expect(api.t('startWaiting')).toBe('Waiting to start');
  });
});
