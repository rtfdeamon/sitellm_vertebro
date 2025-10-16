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

  if (!hasCatalogUi && !hasServersUi) {
    const noopAsync = async () => {};
    global.refreshOllamaCatalog = noopAsync;
    global.refreshOllamaServers = noopAsync;
    global.loadLlmModels = noopAsync;
    global.populateModelOptions = () => {};
    return;
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

  function setAvailabilityMessage(message) {
    if (!availabilityEl) return;
    availabilityEl.textContent = message;
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
    if (!datalist) return;
    const currentInput = doc.getElementById('projectModel');
    const currentValue = typeof selected === 'string' && selected
      ? selected
      : (currentInput && typeof currentInput.value === 'string' ? currentInput.value.trim() : '');

    const values = modelOptions.slice();
    if (currentValue && !values.includes(currentValue)) {
      values.unshift(currentValue);
    }

    datalist.innerHTML = '';
    values.forEach((model) => {
      const option = doc.createElement('option');
      option.value = model;
      datalist.appendChild(option);
    });
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

  function renderInstalled(models) {
    if (!installedListEl) return;
    installedListEl.innerHTML = '';
    const items = Array.isArray(models) ? models : [];
    if (!items.length) {
      const empty = doc.createElement('li');
      empty.textContent = translate('ollamaInstalledEmpty', 'No models installed.');
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
      empty.textContent = translate('ollamaPopularEmpty', 'No recommended models.');
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
        tag.textContent = translate('ollamaServerToggleOn', 'Enabled');
        li.appendChild(tag);
      } else {
        const button = doc.createElement('button');
        button.type = 'button';
        button.className = 'ollama-install-btn';
        button.textContent = installingSet.has(item.name)
          ? translate('ollamaInstalling', 'Installing…')
          : translate('ollamaInstallButton', 'Install');
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
      empty.textContent = translate('ollamaJobsEmpty', 'No active installations.');
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
          parts.push(job.error);
        } else if (Array.isArray(job.log) && job.log.length) {
          parts.push(job.log[job.log.length - 1]);
        }
        wrapper.textContent = parts.join(' · ');
        jobsListEl.appendChild(wrapper);
      });
  }

  function renderCatalogPayload(payload) {
    if (!hasCatalogUi) return;
    const available = Boolean(payload?.available);
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
      setAvailabilityMessage(
        translate('ollamaCatalogSummary', 'Ollama command available. Models installed: {count}.', {
          count: installed.length,
        }),
      );
    } else if (installed.length) {
      setAvailabilityMessage(translate('ollamaCatalogUnavailable', 'Catalog unavailable: ollama command not found, but models detected.'));
    } else {
      setAvailabilityMessage(translate('ollamaCommandMissing', 'Ollama command not found on the server.'));
    }

    renderInstalled(installed);
    renderPopular(popular, installingSet);
    renderJobs(jobs);

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
    setAvailabilityMessage(translate('ollamaCatalogRefreshing', 'Refreshing catalog…'));
    clearCatalogPoll();
    try {
      const response = await fetch('/api/v1/admin/ollama/catalog');
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      const data = await response.json();
      renderCatalogPayload(data);
    } catch (error) {
      console.error('ollama_catalog_load_failed', error);
      setAvailabilityMessage(
        translate('ollamaCatalogLoadError', 'Failed to load catalog: {error}', {
          error: error.message || error,
        }),
      );
      toggleCatalogVisibility(false);
    } finally {
      catalogLoading = false;
    }
  }

  async function installModel(model, control) {
    if (!model) return;
    if (control) {
      control.disabled = true;
      control.textContent = translate('ollamaInstalling', 'Installing…');
    }
    try {
      const response = await fetch('/api/v1/admin/ollama/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      });
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      setAvailabilityMessage(
        translate('ollamaServerInstallStarted', 'Model {model} installation started.', { model })
      );
      await refreshOllamaCatalog(true);
    } catch (error) {
      console.error('ollama_install_failed', error);
      setAvailabilityMessage(
        translate('ollamaActionInstallError', 'Install error: {error}', {
          error: `${model}: ${error.message || error}`,
        }),
      );
      if (control) {
        control.disabled = false;
        control.textContent = translate('ollamaInstallButton', 'Install');
      }
    }
  }

  function renderServers(list) {
    if (!hasServersUi) return;
    serversListEl.innerHTML = '';
    const servers = Array.isArray(list) ? list : [];
    if (!servers.length) {
      const empty = doc.createElement('li');
      empty.textContent = translate('ollamaServersNone', 'No servers configured.');
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
          err.textContent = translate('ollamaActionGeneralError', 'Error: {error}', {
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
        toggleText.textContent = server.enabled
          ? translate('ollamaServerToggleOn', 'Enabled')
          : translate('ollamaServerToggleOff', 'Disabled');
        toggleWrap.appendChild(toggleText);
        row.appendChild(toggleWrap);

        const actions = doc.createElement('div');
        actions.className = 'ollama-server-actions';
        const removeBtn = doc.createElement('button');
        removeBtn.type = 'button';
        removeBtn.textContent = translate('ollamaButtonDelete', 'Delete');
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
    serversStatusEl.textContent = total
      ? translate('ollamaServersSummary', 'Total: {total}. Enabled: {enabled}. Available: {active}.', {
          total,
          enabled,
          active,
        })
      : translate('ollamaServersEmpty', 'No Ollama servers registered.');
  }

  async function refreshOllamaServers() {
    if (!hasServersUi) return;
    if (serversLoading) return;
    serversLoading = true;
    serversStatusEl.textContent = translate('ollamaRefreshUpdating', 'Refreshing list…');
    try {
      const response = await fetch('/api/v1/admin/ollama/servers');
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      const data = await response.json();
      renderServers(data?.servers || []);
      if (serversPanelEl) {
        serversPanelEl.style.display = 'flex';
      }
    } catch (error) {
      console.error('ollama_servers_load_failed', error);
      serversStatusEl.textContent = translate('ollamaRefreshError', 'Refresh error: {error}', {
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
      serversStatusEl.textContent = translate('ollamaServerFormInvalid', 'Specify server name and address.');
      return;
    }
    serversStatusEl.textContent = translate('ollamaServerSaving', 'Saving server…');
    try {
      const response = await fetch('/api/v1/admin/ollama/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      serversStatusEl.textContent = translate('ollamaServerSaved', 'Server saved.');
      await refreshOllamaServers();
    } catch (error) {
      console.error('ollama_server_save_failed', error);
      serversStatusEl.textContent = translate('ollamaActionSaveError', 'Save error: {error}', {
        error: error.message || error,
      });
    }
  }

  async function deleteServer(name) {
    const trimmed = (name || '').trim();
    if (!trimmed) return;
    serversStatusEl.textContent = translate('ollamaServerDeleting', 'Deleting server…');
    try {
      const response = await fetch(`/api/v1/admin/ollama/servers/${encodeURIComponent(trimmed)}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      serversStatusEl.textContent = translate('ollamaServerDeleted', 'Server deleted.');
      await refreshOllamaServers();
    } catch (error) {
      console.error('ollama_server_delete_failed', error);
      serversStatusEl.textContent = translate('ollamaActionDeleteError', 'Delete error: {error}', {
        error: error.message || error,
      });
    }
  }

  async function toggleServerEnabled(name, baseUrl, enabled) {
    if (!name || !baseUrl) return;
    serversStatusEl.textContent = enabled
      ? translate('ollamaServerUpdatingState', 'Enabling server…')
      : translate('ollamaServerDisabling', 'Disabling server…');
    try {
      const response = await fetch('/api/v1/admin/ollama/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          base_url: baseUrl,
          enabled,
        }),
      });
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      serversStatusEl.textContent = translate('ollamaServerUpdated', 'Server state updated.');
      await refreshOllamaServers();
    } catch (error) {
      console.error('ollama_server_toggle_failed', error);
      serversStatusEl.textContent = translate('ollamaActionUpdateError', 'Update error: {error}', {
        error: error.message || error,
      });
      await refreshOllamaServers();
    }
  }

  async function loadLlmModels() {
    try {
      const response = await fetch('/api/v1/admin/llm/models');
      if (!response.ok) {
        throw new Error(await parseError(response));
      }
      const data = await response.json();
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

  global.addEventListener('beforeunload', () => {
    clearCatalogPoll();
  });
})(window);
