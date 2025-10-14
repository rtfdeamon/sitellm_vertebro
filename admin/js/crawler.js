(function (global) {
  const form = document.getElementById('crawler-form');
  const stopBtn = document.getElementById('stopBtn');
  const crawlerProgressFill = document.getElementById('crawlerProgressFill');
  const crawlerProgressStatus = document.getElementById('crawlerProgressStatus');
  const crawlerProgressCounters = document.getElementById('crawlerProgressCounters');
  const crawlerProgressNote = document.getElementById('crawlerProgressNote');
  const crawlerLogsBtn = document.getElementById('crawlerLogsBtn');
  const crawlerLogsPanel = document.getElementById('crawlerLogsPanel');
  const crawlerLogsOutput = document.getElementById('crawlerLogsOutput');
  const crawlerLogsRefresh = document.getElementById('crawlerLogsRefresh');
  const crawlerLogsClose = document.getElementById('crawlerLogsClose');
  const crawlerLogsCopy = document.getElementById('crawlerLogsCopy');
  const crawlerResetBtn = document.getElementById('crawlerResetBtn');
  const crawlerDedupBtn = document.getElementById('crawlerDedupBtn');
  const crawlerActionStatus = document.getElementById('crawlerActionStatus');
  const crawlerCollectBooks = document.getElementById('crawlerCollectBooks');
  const crawlerCollectMedex = document.getElementById('crawlerCollectMedex');
  const launchMsg = document.getElementById('launchMsg');
  const projectDomainInput = document.getElementById('projectDomain');

  const CRAWLER_LOG_REFRESH_INTERVAL = 5000;
  let lastCrawlerLogFetch = 0;
  let crawlerLogsLoading = false;
  let crawlerActionTimer = null;

  const translate = (key, fallback = '', params = null) => {
    if (typeof global.t === 'function') {
      try {
        return params ? global.t(key, params) : global.t(key);
      } catch (error) {
        console.warn('crawler_translate_failed', error);
      }
    }
    if (fallback && params && typeof fallback === 'string') {
      return fallback.replace(/\{(\w+)\}/g, (_, token) =>
        Object.prototype.hasOwnProperty.call(params, token) ? String(params[token]) : '',
      );
    }
    return fallback || key;
  };

  const resetCrawlerProgress = () => {
    if (crawlerProgressFill) crawlerProgressFill.style.width = '0%';
    if (crawlerProgressStatus) crawlerProgressStatus.textContent = translate('crawlerStatusWaiting', 'Waiting to start');
    if (crawlerProgressCounters) {
      crawlerProgressCounters.textContent = translate('crawlerProgressCounters', '0 / 0 pages', { completed: 0, total: 0 });
    }
    if (crawlerProgressNote) {
      crawlerProgressNote.textContent = '';
      crawlerProgressNote.style.display = 'none';
    }
  };

  const setCrawlerProgressError = (message = translate('crawlerFetchError', 'Failed to fetch crawler data')) => {
    if (crawlerProgressFill) crawlerProgressFill.style.width = '0%';
    if (crawlerProgressStatus) crawlerProgressStatus.textContent = translate('crawlerStatusError', 'Status error');
    if (crawlerProgressCounters) crawlerProgressCounters.textContent = '—';
    if (crawlerProgressNote) {
      crawlerProgressNote.textContent = message;
      crawlerProgressNote.style.display = 'block';
    }
  };

  const updateCrawlerProgress = (active, queued, done, failed, note, lastUrl) => {
    if (crawlerProgressFill) {
      const total = Math.max(active + queued + done + failed, 0);
      const completed = Math.max(done, 0);
      const percent = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;
      crawlerProgressFill.style.width = `${percent}%`;
    }
    if (crawlerProgressStatus) {
      let statusText = translate('crawlerStatusWaiting', 'Waiting to start');
      if (active > 0) statusText = translate('crawlerStatusScanning', 'Scanning ({value})', { value: active });
      else if (queued > 0) statusText = translate('crawlerStatusQueuedDetailed', 'Queued ({value})', { value: queued });
      else if (failed > 0) statusText = translate('crawlerErrorsShort', 'Errors');
      else if (done > 0) statusText = translate('crawlerDoneShort', 'Done');
      crawlerProgressStatus.textContent = statusText;
    }
    if (crawlerProgressCounters) {
      const total = Math.max(active + queued + done + failed, 0);
      const completed = Math.max(done, 0);
      const base = total > 0
        ? translate('crawlerProgressCounters', '{completed} / {total} pages', { completed, total })
        : translate('crawlerProgressCounters', '0 / 0 pages', { completed: 0, total: 0 });
      crawlerProgressCounters.textContent = failed > 0
        ? translate('crawlerProgressCountersFailed', '{base} · errors: {failed}', { base, failed })
        : base;
    }
    if (crawlerProgressNote) {
      const bits = [];
      if (note) bits.push(String(note));
      if (lastUrl) bits.push(translate('crawlerLastUrlLabel', 'Last URL: {value}', { value: lastUrl }));
      crawlerProgressNote.textContent = bits.join('\n');
      crawlerProgressNote.style.display = bits.length ? 'block' : 'none';
    }
  };

  const setCrawlerActionStatus = (message = '', timeout = 3000) => {
    if (!crawlerActionStatus) return;
    if (crawlerActionTimer) {
      clearTimeout(crawlerActionTimer);
      crawlerActionTimer = null;
    }
    crawlerActionStatus.textContent = message || '';
    if (timeout > 0 && message) {
      crawlerActionTimer = setTimeout(() => {
        crawlerActionStatus.textContent = '';
        crawlerActionTimer = null;
      }, timeout);
    }
  };

  const refreshCrawlerLogs = async (force = false) => {
    if (!crawlerLogsOutput) return;
    const now = Date.now();
    if (!force && !crawlerLogsPanel?.classList.contains('visible')) return;
    if (!force && now - lastCrawlerLogFetch < CRAWLER_LOG_REFRESH_INTERVAL) return;
    if (crawlerLogsLoading) return;
    crawlerLogsLoading = true;
    crawlerLogsOutput.textContent = translate('crawlerLogsLoading', 'Loading…');
    try {
      const resp = await fetch('/api/v1/admin/logs?limit=400');
      if (!resp.ok) throw new Error('logs request failed');
      const data = await resp.json();
      const lines = Array.isArray(data.lines) ? data.lines : [];
      const filtered = lines.filter((line) => /crawler/i.test(line));
      crawlerLogsOutput.textContent = filtered.length
        ? filtered.join('\n')
        : translate('crawlerLogsEmptyState', 'Crawler logs are empty.');
    } catch (error) {
      console.error('crawler logs fetch failed', error);
      crawlerLogsOutput.textContent = translate('crawlerLogsLoadError', 'Failed to load crawler logs');
    } finally {
      crawlerLogsLoading = false;
      lastCrawlerLogFetch = Date.now();
    }
  };

  const buildCrawlerActionUrl = (path) => {
    const base = `/api/v1/crawler${path}`;
    if (global.currentProject) {
      return `${base}?project=${encodeURIComponent(global.currentProject)}`;
    }
    return base;
  };

  const performCrawlerAction = async (path, successMessage) => {
    if (!global.currentProject) {
      setCrawlerActionStatus(translate('crawlerSelectProject', 'Select a project'), 2500);
      return;
    }
    setCrawlerActionStatus(translate('crawlerActionProcessing', 'Processing…'), 0);
    try {
      const resp = await fetch(buildCrawlerActionUrl(path), { method: 'POST' });
      if (!resp.ok) {
        const text = await resp.text().catch(() => '');
        throw new Error(text || `HTTP ${resp.status}`);
      }
      setCrawlerActionStatus(successMessage, 2000);
      await pollStatus();
      await refreshCrawlerLogs(true);
    } catch (error) {
      console.error('crawler_action_failed', error);
      setCrawlerActionStatus(translate('crawlerActionExecuteError', 'Failed to execute action'), 3000);
    }
  };

  const showCrawlerLogs = () => {
    if (!crawlerLogsPanel) return;
    crawlerLogsPanel.classList.add('visible');
    refreshCrawlerLogs(true);
  };

  const hideCrawlerLogs = () => {
    if (!crawlerLogsPanel) return;
    crawlerLogsPanel.classList.remove('visible');
  };

  const pollStatus = async () => {
    if (!global.currentProject) {
      const clear = (id, value = '0') => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      };
      clear('queued');
      clear('in_progress');
      clear('done');
      clear('failed');
      const lastCrawl = document.getElementById('last_crawl');
      if (lastCrawl) lastCrawl.textContent = 'Last: –';
      const recent = document.getElementById('recent_urls');
      if (recent) recent.innerHTML = '';
        if (typeof global.setSummaryCrawler === 'function') {
          global.setSummaryCrawler(
            translate('projectsNoData', 'No data'),
            translate('crawlerSelectProjectHint', 'Select a project on the left'),
          );
        }
      resetCrawlerProgress();
      return;
    }
    try {
      const url = `/api/v1/crawler/status?project=${encodeURIComponent(global.currentProject)}`;
      const resp = await fetch(url);
      if (resp.ok) {
        const data = await resp.json();
        const crawlerData = data.crawler || {};
        const setVal = (id, value) => {
          const el = document.getElementById(id);
          if (el) el.textContent = value;
        };
        setVal('queued', data.queued ?? 0);
        setVal('in_progress', data.in_progress ?? 0);
        setVal('done', data.done ?? 0);
        setVal('failed', data.failed ?? 0);
        const iso = data.last_crawl_iso || '–';
        const lastCrawl = document.getElementById('last_crawl');
        if (lastCrawl) lastCrawl.textContent = translate('crawlerLast', 'Last: {value}', { value: iso });
        const list = document.getElementById('recent_urls');
        if (list) {
          list.innerHTML = '';
          const arr = (data.crawler && data.crawler.recent_urls) || data.recent_urls || [];
          const uniqueUrls = [];
          const seenUrls = new Set();
          for (const candidate of arr) {
            const trimmed = (candidate || '').trim();
            if (!trimmed || seenUrls.has(trimmed)) continue;
            seenUrls.add(trimmed);
            uniqueUrls.push(trimmed);
          }
          uniqueUrls.forEach((urlValue) => {
            const li = document.createElement('li');
            const anchor = document.createElement('a');
            anchor.href = urlValue;
            anchor.textContent = urlValue;
            anchor.target = '_blank';
            anchor.rel = 'noopener';
            li.appendChild(anchor);
            list.appendChild(li);
          });
        }
        const active = Number(data.in_progress ?? 0);
        const queued = Number(data.queued ?? 0);
        const done = Number(data.done ?? 0);
        const failed = Number(data.failed ?? 0);
        if (typeof global.setSummaryCrawler === 'function') {
          const summaryMain = `${translate('crawlerInProgress', 'In progress: {value}', { value: active })} · ${translate('crawlerQueued', 'Queued: {value}', { value: queued })}`;
          const metaLines = [
            translate('crawlerDone', 'Done: {value}', { value: done }),
            translate('crawlerFailed', 'Failed: {value}', { value: failed }),
          ];
          if (data.last_url) metaLines.push(translate('crawlerLast', 'Last: {value}', { value: data.last_url }));
          if (iso && iso !== '–') metaLines.push(translate('crawlerLastRun', 'Last run: {value}', { value: iso }));
          global.setSummaryCrawler(summaryMain, metaLines.join('\n'));
        }
        updateCrawlerProgress(
          active,
          queued,
          done,
          failed,
          data.notes || crawlerData.notes || '',
          data.last_url || crawlerData.last_url || ''
        );
        if (crawlerLogsPanel?.classList.contains('visible')) {
          refreshCrawlerLogs();
        }
      } else {
        setCrawlerProgressError(translate('crawlerStatusFetchFailed', 'Failed to fetch crawler status'));
      }
    } catch (error) {
      console.error('poll_status_failed', error);
      if (typeof global.setSummaryCrawler === 'function') {
        global.setSummaryCrawler(
          translate('crawlerGenericError', 'Error'),
          translate('crawlerStatusFetchFailed', 'Failed to fetch crawler status'),
        );
      }
      setCrawlerProgressError();
    }
  };

  const pollHealth = async () => {
    try {
      const resp = await fetch('/health');
      if (!resp.ok) return;
      const data = await resp.json();
      const details = data.details || {};
      const set = (id, ok) => {
        const el = document.getElementById(id);
        if (!el) return;
        const error = details[id] && details[id].error ? details[id].error : '';
        el.textContent = ok ? 'up' : 'down';
        el.className = ok ? 'ok' : 'bad';
        el.title = error;
      };
      set('mongo', !!data.mongo);
      set('redis', !!data.redis);
      set('qdrant', !!data.qdrant);
      const overall = document.getElementById('overall');
      if (overall) overall.textContent = data.status || 'unknown';
    } catch (error) {
      console.error('poll_health_failed', error);
    }
  };

  const handleCrawlerSubmit = async (event) => {
    if (!form) return;
    event.preventDefault();
    if (!launchMsg) return;
    const payload = {
      start_url: document.getElementById('url')?.value,
      max_depth: Number(document.getElementById('depth')?.value),
      max_pages: Number(document.getElementById('pages')?.value),
    };
    if (crawlerCollectBooks) payload.collect_books = crawlerCollectBooks.checked;
    if (crawlerCollectMedex) payload.collect_medex = crawlerCollectMedex.checked;
    if (!global.currentProject) {
      launchMsg.textContent = translate('crawlerSelectProject', 'Select a project');
      launchMsg.style.color = 'var(--danger)';
      return;
    }
    payload.project = global.currentProject;
    const crawlDomain = projectDomainInput?.value?.trim();
    if (crawlDomain) payload.domain = crawlDomain;
    resetCrawlerProgress();
    launchMsg.textContent = translate('crawlerStarting', 'Starting…');
    launchMsg.style.color = '';
    try {
      const res = await fetch('/api/v1/crawler/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      launchMsg.textContent = translate('crawlerStarted', 'Crawler started');
      await pollStatus();
    } catch (error) {
      console.error('crawler_start_failed', error);
      launchMsg.textContent = translate('crawlerStartFailed', 'Failed to start crawler');
      launchMsg.style.color = 'var(--danger)';
    }
  };

  const handleCrawlerStop = async () => {
    if (!stopBtn || !launchMsg) return;
    stopBtn.disabled = true;
    try {
      const resp = await fetch('/api/v1/crawler/stop', { method: 'POST' });
      if (!resp.ok) throw new Error(await resp.text());
      setCrawlerProgressError(translate('crawlerStoppedByRequest', 'Stopped on request'));
      launchMsg.textContent = translate('crawlerStopping', 'Stopping…');
    } catch (error) {
      console.error('crawler_stop_failed', error);
      setCrawlerProgressError(translate('crawlerStopFailed', 'Failed to stop crawler'));
      launchMsg.textContent = translate('crawlerStopError', 'Failed to stop');
    } finally {
      stopBtn.disabled = false;
    }
  };

  const bindEvents = () => {
    if (form) form.addEventListener('submit', handleCrawlerSubmit);
    if (stopBtn) stopBtn.addEventListener('click', handleCrawlerStop);
    if (crawlerLogsBtn) {
      crawlerLogsBtn.addEventListener('click', () => {
        if (!crawlerLogsPanel) return;
        if (crawlerLogsPanel.classList.contains('visible')) {
          hideCrawlerLogs();
        } else {
          showCrawlerLogs();
        }
      });
    }
    if (crawlerLogsClose) crawlerLogsClose.addEventListener('click', hideCrawlerLogs);
    if (crawlerLogsRefresh) crawlerLogsRefresh.addEventListener('click', () => refreshCrawlerLogs(true));
    if (crawlerLogsCopy) {
      crawlerLogsCopy.addEventListener('click', async () => {
        const text = crawlerLogsOutput?.textContent || '';
        if (!text.trim()) {
          setCrawlerActionStatus(translate('crawlerActionNoData', 'No data'), 2000);
          return;
        }
        try {
          if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
          } else {
            const selection = window.getSelection();
            if (!selection) throw new Error('selection_unavailable');
            const range = document.createRange();
            range.selectNodeContents(crawlerLogsOutput);
            selection.removeAllRanges();
            selection.addRange(range);
            const ok = document.execCommand('copy');
            selection.removeAllRanges();
            if (!ok) throw new Error('exec_command_failed');
          }
          setCrawlerActionStatus(translate('logCopySuccess', 'Logs copied'), 2000);
        } catch (error) {
          console.error('crawler_logs_copy_failed', error);
          setCrawlerActionStatus(translate('logCopyError', 'Failed to copy'), 3000);
        }
      });
    }
    if (crawlerResetBtn) {
      crawlerResetBtn.addEventListener('click', () => performCrawlerAction('/reset', translate('crawlerActionReset', 'Counters reset')));
    }
    if (crawlerDedupBtn) {
      crawlerDedupBtn.addEventListener('click', () => performCrawlerAction('/deduplicate', translate('crawlerActionDedup', 'Duplicates removed')));
    }
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && crawlerLogsPanel?.classList.contains('visible')) {
        hideCrawlerLogs();
      }
    });
  };

  const init = () => {
    if (global.CrawlerModule?.__initialized) return;
    bindEvents();
    resetCrawlerProgress();
    global.CrawlerModule = {
      resetCrawlerProgress,
      setCrawlerProgressError,
      updateCrawlerProgress,
      setCrawlerActionStatus,
      refreshCrawlerLogs,
      performCrawlerAction,
      showCrawlerLogs,
      hideCrawlerLogs,
      pollStatus,
      pollHealth,
      __initialized: true,
    };
    global.resetCrawlerProgress = resetCrawlerProgress;
    global.setCrawlerProgressError = setCrawlerProgressError;
    global.updateCrawlerProgress = updateCrawlerProgress;
    global.setCrawlerActionStatus = setCrawlerActionStatus;
    global.refreshCrawlerLogs = refreshCrawlerLogs;
    global.performCrawlerAction = performCrawlerAction;
    global.showCrawlerLogs = showCrawlerLogs;
    global.hideCrawlerLogs = hideCrawlerLogs;
    global.pollStatus = pollStatus;
    global.pollHealth = pollHealth;
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})(window);
