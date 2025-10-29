import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const loadUiUtils = async () => {
  vi.resetModules();
  delete window.UIUtils;
  await import('../js/ui-utils.js');
  return window.UIUtils;
};

describe('UIUtils', () => {
  beforeEach(() => {
    vi.stubGlobal('location', {
      origin: 'https://example.com',
      protocol: 'https:',
      href: 'https://example.com/admin/',
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('форматирует байты с выбором единицы', async () => {
    const utils = await loadUiUtils();
    expect(utils.formatBytes(0)).toBe('0 B');
    expect(utils.formatBytes(1024)).toBe('1 KB');
    expect(utils.formatBytes(1024 * 1024 * 5.25)).toBe('5.3 MB');
  });

  it('возвращает тире для необязательного значения', async () => {
    const utils = await loadUiUtils();
    expect(utils.formatBytesOptional(null)).toBe('—');
    expect(utils.formatBytesOptional(2048)).toBe('2 KB');
    expect(utils.formatBytesOptional('invalid')).toBe('—');
  });

  it('форматирует timestamp в строку', async () => {
    const utils = await loadUiUtils();
    const iso = '2024-06-01T12:30:45Z';
    const timestamp = Date.parse(iso);
    expect(utils.formatTimestamp(timestamp)).toContain('2024');
    expect(utils.formatTimestamp(timestamp / 1000)).toContain('2024');
    expect(utils.formatTimestamp('не число')).toBe('—');
  });

  it('строит путь до виджета', async () => {
    const utils = await loadUiUtils();
    expect(utils.getDefaultWidgetPath('Demo')).toBe('/widget?project=demo');
    expect(utils.getDefaultWidgetPath('')).toBe('');
  });

  it('резолвит ссылку на виджет с учётом протокола и origin', async () => {
    const utils = await loadUiUtils();
    expect(utils.resolveWidgetHref('https://demo.example/widget')).toBe('https://demo.example/widget');
    expect(utils.resolveWidgetHref('//cdn.example/assets')).toBe('https://cdn.example/assets');
    expect(utils.resolveWidgetHref('/widget?project=demo')).toBe('https://example.com/widget?project=demo');
    expect(utils.resolveWidgetHref('custom/path')).toBe('https://example.com/custom/path');
    expect(utils.resolveWidgetHref('')).toBeNull();
  });

  it('пульсирует карточку и сбрасывает класс', async () => {
    const utils = await loadUiUtils();
    vi.useFakeTimers();
    const card = document.createElement('div');
    card.classList.add('updated');
    utils.pulseCard(card);
    expect(card.classList.contains('updated')).toBe(true);
    vi.runOnlyPendingTimers();
    expect(card.classList.contains('updated')).toBe(false);
  });

  it('возвращает 0 B для отрицательных значений', async () => {
    const utils = await loadUiUtils();
    expect(utils.formatBytes(-512)).toBe('0 B');
    expect(utils.formatBytesOptional(-512)).toBe('—');
  });

  it('нормализует относительные ссылки с лишними слэшами', async () => {
    const utils = await loadUiUtils();
    expect(utils.resolveWidgetHref('///nested/path')).toBe('https://example.com/nested/path');
  });
});
