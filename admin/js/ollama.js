(function (global) {
  const doc = global.document;

  const catalogRoot = doc.getElementById('ollamaCatalog');
  const refreshCatalogBtn = doc.getElementById('ollamaRefresh');
  const availabilityEl = doc.getElementById('ollamaAvailability');
  const installedListEl = doc.getElementById('ollamaInstalledList');
  const popularListEl = doc.getElementById('ollamaPopularList');
  const jobsListEl = doc.getElementById('ollamaJobsList');
  const serversPanelEl = doc.getElementById('ollamaServersPanel');
  const serversListEl = doc.getElementById('ollamaServersList');
  const serversStatusEl = doc.getElementById('ollamaServersStatus');
  const serversRefreshBtn = doc.getElementById('ollamaServersRefresh');
  const serverForm = doc.getElementById('ollamaServerForm');
  const serverNameInput = doc.getElementById('ollamaServerName');
  const serverUrlInput = doc.getElementById('ollamaServerUrl');
  const serverEnabledInput = doc.getElementById('ollamaServerEnabled');

  const hasCatalogUi = Boolean(catalogRoot && availabilityEl && installedListEl && popularListEl && jobsListEl);
  const hasServersUi = Boolean(serversPanelEl && serversListEl && serversStatusEl);

  const translate = (key, fallback = '', params = null) => {
    if (typeof global.t === 'function') {
      try {
        return params ? global.t(key, params) : global.t(key);
      } catch (error) {
        console.warn('ollama_translate_failed', error);
      }
    }
    if (fallback && params && typeof fallback === 'string') {
      return fallback.replace(/\{(\w+)\}/g, (_, token) =>
        Object.prototype.hasOwnProperty.call(params, token) ? String(params[token]) : '',
      );
    }
    return fallback || key;
  };

  const setNodeText = (node, key, fallback = '', params = null) => {
    if (!node) return;
    node.dataset.i18nKey = key;
    if (fallback) {
      node.dataset.i18nFallback = fallback;
    } else {
      delete node.dataset.i18nFallback;
    }
    if (params && Object.keys(params).length) {
      try {
        node.dataset.i18nParams = JSON.stringify(params);
      } catch {
        delete node.dataset.i18nParams;
      }
    } else {
      delete node.dataset.i18nParams;
    }
    node.textContent = translate(key, fallback, params);
  };

  const reapplyStoredTranslations = (root = doc) => {
    const scope = root || doc;
    scope.querySelectorAll('[data-i18n-key]').forEach((node) => {
      const key = node.dataset.i18nKey;
      const fallback = node.dataset.i18nFallback || '';
      let params = null;
      if (node.dataset.i18nParams) {
        try {
          params = JSON.parse(node.dataset.i18nParams);
        } catch {
          params = null;
        }
      }
      node.textContent = translate(key, fallback, params);
    });
  };

  if (!hasCatalogUi && !hasServersUi) {
    const noopAsync = async () => {};
    global.refreshOllamaCatalog = noopAsync;
    global.refreshOllamaServers = noopAsync;
    global.loadLlmModels = noopAsync;
    global.populateModelOptions = () => {};
  }

  const JOB_ACTIVE_STATUSES = new Set(['pending', 'running']);
  const JOB_CLASSES = {
    pending: 'pending',
    running: 'running',
    success: 'success',
    error: 'error',
  };
  const JOB_TITLES = {
    pending: translate('ollamaJobPending', 'Pending'),
    running: translate('ollamaJobRunning', 'Installing…'),
    success: translate('ollamaJobSuccess', 'Installed'),
    error: translate('ollamaJobError', 'Installation failed'),
  };

  let catalogLoading = false;
  let serversLoading = false;
  let catalogPollTimer = null;
  let modelOptions = [];
  let lastCatalogPayload = null;
  let lastServersSnapshot = null;

  function clearCatalogPoll() {
    if (catalogPollTimer) {
      global.clearTimeout(catalogPollTimer);
      catalogPollTimer = null;
    }
  }

  function scheduleCatalogPoll(hasActiveJobs) {
    clearCatalogPoll();
    if (!hasCatalogUi || !hasActiveJobs) return;
    catalogPollTimer = global.setTimeout(() => {
      refreshOllamaCatalog(true);
    }, 4000);
  }

  function setAvailabilityMessage(key, fallback, params = null) {
    if (!availabilityEl) return;
    setNodeText(availabilityEl, key, fallback, params);
  }

  function toggleCatalogVisibility(visible) {
    if (!catalogRoot) return;
    if (visible) {
      catalogRoot.classList.add('show');
    } else {
      catalogRoot.classList.remove('show');
    }
  }

  function formatTimestamp(value) {
    if (!value) return null;
    let date;
    if (typeof value === 'number') {
      date = new Date(value * 1000);
    } else {
      date = new Date(value);
    }
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleString();
  }

  function formatJobErrorMessage(raw) {
    if (typeof raw !== 'string' || !raw) return null;
    const match = raw.match(/^ollamaJobError:\s*(.+)$/);
    if (!match) {
      return translate('ollamaJobErrorMessage', '{message}', { message: raw });
    }
    const payload = match[1];
    const [modelPart, reasonPart] = payload.split('·').map((part) => part.trim());
    const model = modelPart || '';
    const reason = reasonPart || '';
    return translate('ollamaJobErrorUnavailable', '{model} unavailable on the server', {
      model,
      reason,
    });
  }

  function setModelOptions(options) {
    const unique = Array.from(
      new Set(
        (options || [])
          .map((item) => (typeof item === 'string' ? item.trim() : ''))
          .filter(Boolean),
      ),
    );
    modelOptions = unique;
    populateModelOptions();
  }

  function populateModelOptions(selected) {
    const datalist = doc.getElementById('llmModelOptions');
    const selectEl = doc.getElementById('projectModel');
    const currentValue = typeof selected === 'string' && selected
      ? selected.trim()
      : (selectEl && typeof selectEl.value === 'string' ? selectEl.value.trim() : '');

    console.log('[ollama] populateModelOptions: currentValue', currentValue, 'modelOptions', modelOptions);

    const values = modelOptions.slice();
    if (currentValue && !values.includes(currentValue)) {
      values.unshift(currentValue);
    }

    if (datalist) {
      datalist.innerHTML = '';
      values.forEach((model) => {
        const option = doc.createElement('option');
        option.value = model;
        datalist.appendChild(option);
      });
    }

    if (selectEl) {
      const wasActive = doc.activeElement === selectEl;
      selectEl.innerHTML = '';

      const existing = new Set();

      values.forEach((model) => {
        const option = doc.createElement('option');
        option.value = model;
        option.textContent = model;
        if (currentValue && model === currentValue) {
          option.selected = true;
        }
        selectEl.appendChild(option);
        existing.add(model);
      });

      if (currentValue && !existing.has(currentValue)) {
        const extra = doc.createElement('option');
        extra.value = currentValue;
        extra.textContent = currentValue;
        extra.selected = true;
        selectEl.appendChild(extra);
      }

      if (!selectEl.options.length) {
        const placeholder = doc.createElement('option');
        placeholder.value = '';
        placeholder.textContent = translate('projectsModelPlaceholder', '—');
        placeholder.selected = true;
        selectEl.appendChild(placeholder);
      }

      if (currentValue && selectEl.value !== currentValue) {
        selectEl.value = currentValue;
      }

      console.log('[ollama] populateModelOptions: select values', Array.from(selectEl.options).map((opt) => opt.value));

      if (wasActive && typeof selectEl.focus === 'function') {
        selectEl.focus({ preventScroll: true });
      }
    }
  }

  async function parseError(response) {
    try {
      const data = await response.clone().json();
      if (data && typeof data === 'object' && data.detail) {
        return data.detail;
      }
    } catch {
      /* ignore */
    }
    try {
      const text = await response.text();
      if (text) return text;
    } catch {
      /* ignore */
    }
    return `HTTP ${response.status}`;
  }

  function cloneCatalogPayload(payload) {
    if (!payload || typeof payload !== 'object') {
      return {
        available: false,
        cli_available: false,
        remote_available: false,
        installed: [],
        popular: [],
        jobs: {},
        default_model: null,
      };
    }
    const installed = Array.isArray(payload.installed)
      ? payload.installed.map((item) => ({ ...item }))
      : [];
    const popular = Array.isArray(payload.popular)
      ? payload.popular.map((item) => ({ ...item }))
      : [];
    const jobs = {};
    if (payload.jobs && typeof payload.jobs === 'object') {
      Object.entries(payload.jobs).forEach(([key, job]) => {
        if (job && typeof job === 'object') {
          jobs[key] = {
            ...job,
            log: Array.isArray(job.log) ? job.log.slice() : job.log,
            stderr: Array.isArray(job.stderr) ? job.stderr.slice() : job.stderr,
          };
        } else {
          jobs[key] = job;
        }
      });
    }
    return {
      ...payload,
      available: Boolean(
        Object.prototype.hasOwnProperty.call(payload, 'available')
          ? payload.available
          : payload.cli_available || payload.remote_available,
      ),
      cli_available: Boolean(payload.cli_available),
      remote_available: Boolean(payload.remote_available),
      installed,
      popular,
      jobs,
      default_model: payload.default_model ?? null,
    };
  }

  function cloneServersSnapshot(list) {
    if (!Array.isArray(list)) return [];
    return list.map((server) => ({ ...server }));
  }

  function renderInstalled(models) {
    if (!installedListEl) return;
    installedListEl.innerHTML = '';
    const items = Array.isArray(models) ? models : [];
    if (!items.length) {
      const empty = doc.createElement('li');
      setNodeText(empty, 'ollamaInstalledEmpty', 'No models installed.');
      installedListEl.appendChild(empty);
      return;
    }
    items.forEach((model) => {
      const li = doc.createElement('li');
      const info = doc.createElement('div');
      info.style.display = 'flex';
      info.style.flexDirection = 'column';
      info.style.gap = '2px';

      const title = doc.createElement('strong');
      title.textContent = model.name || '—';
      title.style.fontSize = '13px';
      info.appendChild(title);

      const meta = doc.createElement('span');
      const bits = [];
      if (model.size_human) bits.push(model.size_human);
      const modified = formatTimestamp(model.modified_at);
      if (modified) bits.push(translate('ollamaServerUpdatedAt', 'updated {value}', { value: modified }));
      if (model.digest) bits.push(model.digest.substring(0, 12));
      meta.textContent = bits.length ? bits.join(' · ') : translate('ollamaServerHealthyUnknown', 'unknown');
      meta.className = 'muted';
      meta.style.fontSize = '12px';
      info.appendChild(meta);

      li.appendChild(info);
      installedListEl.appendChild(li);
    });
  }

  function renderPopular(models, installingSet) {
    if (!popularListEl) return;
    popularListEl.innerHTML = '';
    const items = Array.isArray(models) ? models : [];
    if (!items.length) {
      const empty = doc.createElement('li');
      setNodeText(empty, 'ollamaPopularEmpty', 'No recommended models.');
      popularListEl.appendChild(empty);
      return;
    }
    items.forEach((item) => {
      const li = doc.createElement('li');
      const label = doc.createElement('span');
      const size = item.approx_size_human ? ` · ${item.approx_size_human}` : '';
      label.textContent = `${item.name}${size}`;
      li.appendChild(label);

      if (item.installed) {
        const tag = doc.createElement('span');
        tag.className = 'muted';
        tag.style.fontSize = '12px';
        setNodeText(tag, 'ollamaServerToggleOn', 'Enabled');
        li.appendChild(tag);
      } else {
        const button = doc.createElement('button');
        button.type = 'button';
        button.className = 'ollama-install-btn';
        if (installingSet.has(item.name)) {
          setNodeText(button, 'ollamaInstalling', 'Installing…');
        } else {
          setNodeText(button, 'ollamaInstallButton', 'Install');
        }
        button.disabled = installingSet.has(item.name);
        button.dataset.model = item.name;
        li.appendChild(button);
      }

      popularListEl.appendChild(li);
    });
  }

  function renderJobs(jobs) {
    if (!jobsListEl) return;
    jobsListEl.innerHTML = '';
    const list = jobs && typeof jobs === 'object' ? Object.values(jobs) : [];
    if (!list.length) {
      const empty = doc.createElement('div');
      empty.className = 'muted';
      setNodeText(empty, 'ollamaJobsEmpty', 'No active installations.');
      jobsListEl.appendChild(empty);
      return;
    }

    list
      .sort((a, b) => {
        const aTime = typeof a.started_at === 'number' ? a.started_at : 0;
        const bTime = typeof b.started_at === 'number' ? b.started_at : 0;
        return bTime - aTime;
      })
      .forEach((job) => {
        const wrapper = doc.createElement('div');
        const status = (job.status || 'pending').toLowerCase();
        wrapper.className = `ollama-job ${JOB_CLASSES[status] || 'pending'}`;

        const progress = typeof job.progress === 'number' ? Math.round(job.progress) : null;
        const statusLabel = JOB_TITLES[status] || JOB_TITLES.pending;
        const parts = [`${statusLabel}: ${job.model || '—'}`];
        if (status === 'running' && progress !== null) {
          parts.push(`${progress}%`);
        }
        if (status === 'error' && job.error) {
          const message = formatJobErrorMessage(job.error);
          if (message) {
            parts.push(message);
          }
        } else if (Array.isArray(job.log) && job.log.length) {
          parts.push(job.log[job.log.length - 1]);
        }
        wrapper.textContent = parts.join(' · ');
        jobsListEl.appendChild(wrapper);
      });
  }

  function renderCatalogPayload(payload) {
    if (!hasCatalogUi) return;
    const cliAvailable = Boolean(payload?.cli_available);
    const remoteAvailable = Boolean(payload?.remote_available);
    const available = Boolean(
      Object.prototype.hasOwnProperty.call(payload || {}, 'available')
        ? payload.available
        : cliAvailable || remoteAvailable,
    );
    const installed = Array.isArray(payload?.installed) ? payload.installed : [];
    const popular = Array.isArray(payload?.popular) ? payload.popular : [];
    const jobs = payload?.jobs || {};

    const installingSet = new Set(
      Object.values(jobs || {})
        .filter((job) => job && JOB_ACTIVE_STATUSES.has((job.status || '').toLowerCase()))
        .map((job) => job.model)
        .filter(Boolean),
    );

    toggleCatalogVisibility(available || installed.length || popular.length || Object.keys(jobs).length);

    if (available) {
      const params = { count: installed.length };
      if (cliAvailable && remoteAvailable) {
        setAvailabilityMessage(
          'ollamaCatalogHybridSummary',
          'Local CLI and remote Ollama servers available. Models installed: {count}.',
          params,
        );
      } else if (cliAvailable) {
        setAvailabilityMessage('ollamaCatalogSummary', 'Local Ollama CLI available. Models installed: {count}.', params);
      } else if (remoteAvailable) {
        setAvailabilityMessage(
          'ollamaCatalogRemoteSummary',
          'Remote Ollama server available. Models installed: {count}.',
          params,
        );
      } else {
        setAvailabilityMessage('ollamaCatalogSummary', 'Ollama command available. Models installed: {count}.', params);
      }
    } else if (installed.length) {
      setAvailabilityMessage(
        'ollamaCatalogUnavailable',
        'Catalog unavailable: ollama command not found, but models detected.',
      );
    } else {
      setAvailabilityMessage('ollamaCommandMissing', 'Ollama command not found on the server.');
    }

    renderInstalled(installed);
    renderPopular(popular, installingSet);
    renderJobs(jobs);
    reapplyStoredTranslations(catalogRoot);

    const modelNames = [
      ...installed.map((item) => item.name),
      ...popular.map((item) => item.name),
    ];
    setModelOptions(modelNames);

    const hasActiveJobs = Object.values(jobs).some(
      (job) => job && JOB_ACTIVE_STATUSES.has((job.status || '').toLowerCase()),
    );
    scheduleCatalogPoll(hasActiveJobs);
  }

  async function refreshOllamaCatalog(force = false) {
    if (!hasCatalogUi) return;
    if (catalogLoading) return;
    catalogLoading = true;
    setAvailabilityMessage('ollamaCatalogRefreshing', 'Refreshing catalog…');
    clearCatalogPoll();
    try {
      const response = await fetch('/api/v1/admin/ollama/catalog', { credentials: 'same-origin' });
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      const data = await response.json();
      lastCatalogPayload = cloneCatalogPayload(data);
      renderCatalogPayload(lastCatalogPayload);
    } catch (error) {
      console.error('ollama_catalog_load_failed', error);
      setAvailabilityMessage('ollamaCatalogLoadError', 'Failed to load catalog: {error}', {
        error: error.message || error,
      });
      toggleCatalogVisibility(false);
    } finally {
      catalogLoading = false;
    }
  }

  async function installModel(model, control) {
    if (!model) return;
    if (control) {
      control.disabled = true;
      setNodeText(control, 'ollamaInstalling', 'Installing…');
    }
    try {
      const response = await fetch('/api/v1/admin/ollama/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
        credentials: 'same-origin',
      });
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      setAvailabilityMessage('ollamaServerInstallStarted', 'Model {model} installation started.', { model });
      await refreshOllamaCatalog(true);
    } catch (error) {
      console.error('ollama_install_failed', error);
      setAvailabilityMessage('ollamaActionInstallError', 'Install error: {error}', {
        error: `${model}: ${error.message || error}`,
      });
      if (control) {
        control.disabled = false;
        setNodeText(control, 'ollamaInstallButton', 'Install');
      }
    }
  }

  function renderServers(list) {
    if (!hasServersUi) return;
    serversListEl.innerHTML = '';
    const servers = Array.isArray(list) ? list : [];
    if (!servers.length) {
      const empty = doc.createElement('li');
      setNodeText(empty, 'ollamaServersNone', 'No servers configured.');
      serversListEl.appendChild(empty);
    } else {
      servers.forEach((server) => {
        const item = doc.createElement('li');
        const row = doc.createElement('div');
        row.className = 'ollama-server-row';
        if (!server.enabled || !server.healthy) {
          row.classList.add('ollama-server-offline');
        }

        const header = doc.createElement('h4');
        const rawName = typeof server.name === 'string' ? server.name.trim() : '';
        const normalized = rawName.toLowerCase();
        if (normalized === 'default') {
          header.textContent = translate('ollamaServerDefaultTitle', 'Default');
        } else if (rawName) {
          header.textContent = rawName;
        } else {
          header.textContent = translate('ollamaServerUnnamed', 'Unnamed');
        }
        row.appendChild(header);

        const urlLine = doc.createElement('div');
        urlLine.className = 'muted';
        urlLine.style.fontSize = '12px';
        urlLine.textContent = server.base_url || '—';
        row.appendChild(urlLine);

        const meta = doc.createElement('div');
        meta.className = 'ollama-server-meta';
        const statusValue = server.enabled
          ? (server.healthy ? translate('ollamaServerHealthy', 'healthy') : translate('ollamaServerError', 'error'))
          : translate('ollamaServerDisabled', 'disabled');
        const metaBits = [
          [translate('ollamaServerStatusTitle', 'Status'), statusValue],
          [
            translate('ollamaLatencyLabel', 'Latency'),
            server.avg_latency_ms != null
              ? translate('ollamaLatencyValue', '{value} ms', { value: server.avg_latency_ms })
              : '—',
          ],
          [
            translate('ollamaRequestsPerHour', 'Requests/hour'),
            server.requests_last_hour != null ? String(server.requests_last_hour) : '—',
          ],
          [
            translate('ollamaInFlight', 'In flight'),
            server.inflight != null ? String(server.inflight) : '—',
          ],
        ];
        metaBits.forEach(([label, value]) => {
          const span = doc.createElement('span');
          span.textContent = `${label}: ${value}`;
          meta.appendChild(span);
        });
        if (server.last_error) {
          const err = doc.createElement('span');
          setNodeText(err, 'ollamaActionGeneralError', 'Error: {error}', {
            error: server.last_error,
          });
          meta.appendChild(err);
        }
        row.appendChild(meta);

        const toggleWrap = doc.createElement('label');
        toggleWrap.className = 'ollama-server-toggle';
        const toggle = doc.createElement('input');
        toggle.type = 'checkbox';
        toggle.checked = Boolean(server.enabled);
        toggle.dataset.name = server.name || '';
        toggle.dataset.base = server.base_url || '';
        toggle.disabled = Boolean(server.ephemeral);
        toggleWrap.appendChild(toggle);
        const toggleText = doc.createElement('span');
        setNodeText(
          toggleText,
          server.enabled ? 'ollamaServerToggleOn' : 'ollamaServerToggleOff',
          server.enabled ? 'Enabled' : 'Disabled',
        );
        toggleWrap.appendChild(toggleText);
        row.appendChild(toggleWrap);

        const actions = doc.createElement('div');
        actions.className = 'ollama-server-actions';
        const removeBtn = doc.createElement('button');
        removeBtn.type = 'button';
        setNodeText(removeBtn, 'ollamaButtonDelete', 'Delete');
        removeBtn.dataset.name = server.name || '';
        removeBtn.disabled = Boolean(server.ephemeral);
        actions.appendChild(removeBtn);
        row.appendChild(actions);

        item.appendChild(row);
        serversListEl.appendChild(item);
      });
    }

    const total = servers.length;
    const active = servers.filter((server) => server.enabled && server.healthy).length;
    const enabled = servers.filter((server) => server.enabled).length;
    if (total) {
      setNodeText(
        serversStatusEl,
        'ollamaServersSummary',
        'Total: {total}. Enabled: {enabled}. Available: {active}.',
        { total, enabled, active },
      );
    } else {
      setNodeText(serversStatusEl, 'ollamaServersEmpty', 'No Ollama servers registered.');
    }
    reapplyStoredTranslations(serversPanelEl);
  }

  async function refreshOllamaServers() {
    if (!hasServersUi) return;
    if (serversLoading) return;
    serversLoading = true;
    setNodeText(serversStatusEl, 'ollamaRefreshUpdating', 'Refreshing list…');
    try {
      const response = await fetch('/api/v1/admin/ollama/servers', { credentials: 'same-origin' });
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      const data = await response.json();
      const servers = Array.isArray(data?.servers) ? data.servers : [];
      lastServersSnapshot = cloneServersSnapshot(servers);
      renderServers(lastServersSnapshot);
      if (serversPanelEl) {
        serversPanelEl.style.display = 'flex';
      }
    } catch (error) {
      console.error('ollama_servers_load_failed', error);
      setNodeText(serversStatusEl, 'ollamaRefreshError', 'Refresh error: {error}', {
        error: error.message || error,
      });
    } finally {
      serversLoading = false;
    }
  }

  async function upsertServer({ name, base_url: baseUrl, enabled }) {
    const payload = {
      name: (name || '').trim(),
      base_url: (baseUrl || '').trim(),
      enabled: Boolean(enabled),
    };
    if (!payload.name || !payload.base_url) {
      setNodeText(serversStatusEl, 'ollamaServerFormInvalid', 'Specify server name and address.');
      return;
    }
    setNodeText(serversStatusEl, 'ollamaServerSaving', 'Saving server…');
    try {
      const response = await fetch('/api/v1/admin/ollama/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'same-origin',
      });
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      setNodeText(serversStatusEl, 'ollamaServerSaved', 'Server saved.');
      await refreshOllamaServers();
    } catch (error) {
      console.error('ollama_server_save_failed', error);
      setNodeText(serversStatusEl, 'ollamaActionSaveError', 'Save error: {error}', {
        error: error.message || error,
      });
    }
  }

  async function deleteServer(name) {
    const trimmed = (name || '').trim();
    if (!trimmed) return;
    setNodeText(serversStatusEl, 'ollamaServerDeleting', 'Deleting server…');
    try {
      const response = await fetch(`/api/v1/admin/ollama/servers/${encodeURIComponent(trimmed)}`, {
        method: 'DELETE',
        credentials: 'same-origin',
      });
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      setNodeText(serversStatusEl, 'ollamaServerDeleted', 'Server deleted.');
      await refreshOllamaServers();
    } catch (error) {
      console.error('ollama_server_delete_failed', error);
      setNodeText(serversStatusEl, 'ollamaActionDeleteError', 'Delete error: {error}', {
        error: error.message || error,
      });
    }
  }

  async function toggleServerEnabled(name, baseUrl, enabled) {
    if (!name || !baseUrl) return;
    if (enabled) {
      setNodeText(serversStatusEl, 'ollamaServerUpdatingState', 'Enabling server…');
    } else {
      setNodeText(serversStatusEl, 'ollamaServerDisabling', 'Disabling server…');
    }
    try {
      const response = await fetch('/api/v1/admin/ollama/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          base_url: baseUrl,
          enabled,
        }),
        credentials: 'same-origin',
      });
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      setNodeText(serversStatusEl, 'ollamaServerUpdated', 'Server state updated.');
      await refreshOllamaServers();
    } catch (error) {
      console.error('ollama_server_toggle_failed', error);
      setNodeText(serversStatusEl, 'ollamaActionUpdateError', 'Update error: {error}', {
        error: error.message || error,
      });
      await refreshOllamaServers();
    }
  }

  async function loadLlmModels() {
    try {
      console.log('[ollama] loadLlmModels: fetching /api/v1/admin/llm/models');
      const response = await fetch('/api/v1/admin/llm/models', { credentials: 'same-origin' });
      if (!response.ok) {
        console.warn('[ollama] loadLlmModels: non-ok status', response.status);
        throw new Error(await parseError(response));
      }
      const data = await response.json();
      console.log('[ollama] loadLlmModels: payload', data);
      setModelOptions(Array.isArray(data?.models) ? data.models : []);
    } catch (error) {
      console.error('llm_models_load_failed', error);
    }
  }

  if (refreshCatalogBtn) {
    refreshCatalogBtn.addEventListener('click', () => {
      refreshOllamaCatalog(true);
    });
  }

  if (popularListEl) {
    popularListEl.addEventListener('click', (event) => {
      const target = event.target;
      if (target && target.matches('.ollama-install-btn')) {
        const model = target.dataset.model || '';
        installModel(model, target);
      }
    });
  }

  if (serversRefreshBtn) {
    serversRefreshBtn.addEventListener('click', () => {
      refreshOllamaServers();
    });
  }

  if (serverForm) {
    serverForm.addEventListener('submit', (event) => {
      event.preventDefault();
      upsertServer({
        name: serverNameInput ? serverNameInput.value : '',
        base_url: serverUrlInput ? serverUrlInput.value : '',
        enabled: serverEnabledInput ? serverEnabledInput.checked : true,
      }).then(() => {
        if (serverNameInput) serverNameInput.value = '';
        if (serverUrlInput) serverUrlInput.value = '';
        if (serverEnabledInput) serverEnabledInput.checked = true;
      });
    });
  }

  if (serversListEl) {
    serversListEl.addEventListener('click', (event) => {
      const target = event.target;
      if (target && target.tagName === 'BUTTON' && target.dataset.name) {
        deleteServer(target.dataset.name);
      }
    });
    serversListEl.addEventListener('change', (event) => {
      const target = event.target;
      if (target && target.type === 'checkbox' && target.dataset.name) {
        toggleServerEnabled(target.dataset.name, target.dataset.base || '', target.checked);
      }
    });
  }

  global.refreshOllamaCatalog = refreshOllamaCatalog;
  global.refreshOllamaServers = refreshOllamaServers;
  global.loadLlmModels = loadLlmModels;
  global.populateModelOptions = populateModelOptions;
  const renderCatalogFromCache = () => {
    if (lastCatalogPayload) {
      renderCatalogPayload(lastCatalogPayload);
      return true;
    }
    return false;
  };

  const renderServersFromCache = () => {
    if (lastServersSnapshot) {
      renderServers(lastServersSnapshot);
      return true;
    }
    return false;
  };

  const handleLanguageApplied = () => {
    const tasks = [];
    renderCatalogFromCache();
    renderServersFromCache();
    let catalogRendered = false;
    if (typeof refreshOllamaCatalog === 'function' && hasCatalogUi) {
      tasks.push(
        refreshOllamaCatalog(true).catch((error) => {
          console.warn('ollama_language_refresh_catalog_failed', error);
        }),
      );
      catalogRendered = true;
    } else if (renderCatalogFromCache()) {
      catalogRendered = true;
    }

    if (typeof refreshOllamaServers === 'function' && hasServersUi) {
      tasks.push(
        refreshOllamaServers().catch((error) => {
          console.warn('ollama_language_refresh_servers_failed', error);
        }),
      );
    } else {
      renderServersFromCache();
    }

    if (!catalogRendered) {
      populateModelOptions();
    }
    return Promise.allSettled(tasks);
  };
  global.OllamaModule = {
    ...(global.OllamaModule || {}),
    handleLanguageApplied,
    renderCatalogFromCache,
    renderServersFromCache,
  };

  global.addEventListener('beforeunload', () => {
    clearCatalogPoll();
  });
})(window);
