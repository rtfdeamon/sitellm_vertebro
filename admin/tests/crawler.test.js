import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('Crawler module polling', () => {
  let intervalSpy;

  beforeEach(async () => {
    vi.resetModules();
    vi.useFakeTimers();
    intervalSpy = vi.spyOn(global, 'setInterval');

    Object.defineProperty(document, 'readyState', {
      value: 'complete',
      configurable: true,
    });
    Object.defineProperty(document, 'hidden', {
      value: false,
      configurable: true,
    });

    document.body.innerHTML = `
      <div id="crawlerProgressFill"></div>
      <div id="crawlerProgressStatus"></div>
      <div id="crawlerProgressCounters"></div>
    `;
    global.currentProject = 'demo';

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        crawler: { recent_urls: [] },
        queued: 0,
        in_progress: 0,
        done: 0,
        failed: 0,
        note_codes: [],
        last_crawl_iso: '–',
      }),
    });

    await import('../js/crawler.js');
  });

  afterEach(() => {
    vi.useRealTimers();
    intervalSpy.mockRestore();
    delete global.fetch;
    delete global.CrawlerModule;
    delete global.startCrawlerPolling;
    delete global.stopCrawlerPolling;
    delete global.currentProject;
    delete global.onAdminProjectChange;
  });

  it('schedules periodic status polling', async () => {
    await Promise.resolve();
    expect(intervalSpy).toHaveBeenCalledWith(expect.any(Function), 5000);
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/crawler/status?project=demo',
      { cache: 'no-store' },
    );

    await vi.advanceTimersByTimeAsync(5000);
    expect(global.fetch.mock.calls.filter((call) => call[0].startsWith('/api/v1/crawler/status'))).not.toHaveLength(0);
  });
});
