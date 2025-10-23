(function (global) {
  const registry = (global.ProjectIntegrations = global.ProjectIntegrations || {});

  const tokenInput = global.document.getElementById('projectVkToken');
  const autoStartInput = global.document.getElementById('projectVkAutoStart');
  const statusLabel = global.document.getElementById('projectVkStatus');
  const infoLabel = global.document.getElementById('projectVkInfo');
  const messageLabel = global.document.getElementById('projectVkMessage');
  const saveButton = global.document.getElementById('projectVkSave');
  const startButton = global.document.getElementById('projectVkStart');
  const stopButton = global.document.getElementById('projectVkStop');

  let busy = false;
  let lastStatus = null;

  const hasElements =
    tokenInput &&
    autoStartInput &&
    statusLabel &&
    infoLabel &&
    saveButton &&
    startButton &&
    stopButton;

  const fallback = {
    reset() {},
    applyProject() {},
    load() {},
  };

  if (!hasElements) {
    registry.vk = fallback;
    return;
  }

  const formatTemplate = (template, params = {}) => {
    if (typeof template !== 'string') return '';
    return template.replace(/\{(\w+)\}/g, (_, token) => {
      if (Object.prototype.hasOwnProperty.call(params, token)) {
        const replacement = params[token];
        return replacement === null || replacement === undefined ? '' : String(replacement);
      }
      return '';
    });
  };

  const translate = (key, fallback = '', params = undefined) => {
    if (typeof global.t === 'function') {
      try {
        return params ? global.t(key, params) : global.t(key);
      } catch (error) {
        console.warn('vk_translate_failed', error);
      }
    }
    if (fallback) {
      return formatTemplate(fallback, params);
    }
    return key;
  };

  const UPDATE_DELAY_MS = 2400;

  function projectName() {
    return (global.currentProject || '').trim().toLowerCase();
  }

  function setMessage(text, timeout = UPDATE_DELAY_MS) {
    if (!messageLabel) return;
    messageLabel.textContent = text || '';
    if (text && timeout) {
      const snapshot = text;
      global.setTimeout(() => {
        if (messageLabel.textContent === snapshot) {
          messageLabel.textContent = '';
        }
      }, timeout);
    }
  }

  function buildInfo(status) {
    if (!status) {
      return translate('integrationVkSelectProject', 'Select a project to manage the VK bot.');
    }
    const parts = [];
    if (status.token_set) {
      parts.push(
        translate('integrationTokenPreview', 'Token: {value}', {
          value: status.token_preview || '••••',
        }),
      );
    } else {
      parts.push(translate('integrationTokenNotSet', 'Token not set'));
    }
    parts.push(
      translate('integrationAutoStart', 'Auto-start: {value}', {
        value: translate(
          status.auto_start ? 'integrationAutoStartEnabled' : 'integrationAutoStartDisabled',
          status.auto_start ? 'Enabled' : 'Disabled',
        ),
      }),
    );
    if (status.last_error) {
      parts.push(
        translate('integrationLastError', 'Last error: {value}', {
          value: status.last_error,
        }),
      );
    }
    return parts.join(' · ');
  }

  function updatePlaceholder(status) {
    if (!tokenInput) return;
    tokenInput.placeholder = status?.token_set
      ? translate('integrationTokenSavedPlaceholder', 'Token saved')
      : translate('tokenPlaceholder', 'Enter token');
  }

  function updateButtons(status) {
    const selected = Boolean(projectName());
    const running = Boolean(status?.running);
    const disabledBase = !selected || busy;
    if (saveButton) saveButton.disabled = disabledBase;
    if (startButton) startButton.disabled = disabledBase || running;
    if (stopButton) stopButton.disabled = disabledBase || !running;
  }

  function applyStatus(status) {
    lastStatus = status;
    if (!status) {
      statusLabel.textContent = '—';
      infoLabel.textContent = buildInfo(null);
      updateButtons(null);
      updatePlaceholder(null);
      return;
    }
    statusLabel.textContent = status.running
      ? translate('integrationStatusRunning', 'Running')
      : translate('integrationStatusStopped', 'Stopped');
    if (autoStartInput) {
      autoStartInput.checked = !!status.auto_start;
    }
    infoLabel.textContent = buildInfo(status);
    updatePlaceholder(status);
    updateButtons(status);
  }

  function reset() {
    if (tokenInput) {
      tokenInput.value = '';
      tokenInput.placeholder = translate('tokenPlaceholder', 'Enter token');
    }
    if (messageLabel) {
      messageLabel.textContent = '';
    }
    applyStatus(null);
    if (autoStartInput) {
      autoStartInput.checked = false;
    }
  }

  function applyProject(project) {
    lastStatus = null;
    if (tokenInput) {
      tokenInput.value = '';
    }
    if (messageLabel) {
      messageLabel.textContent = '';
    }
    if (autoStartInput) {
      autoStartInput.checked = !!project?.vk_auto_start;
    }
    if (!project || !project.name) {
      applyStatus(null);
    } else if (!lastStatus) {
      infoLabel.textContent = translate(
        'integrationVkSaveHint',
        'Save the token and start the VK bot.',
      );
      updatePlaceholder(null);
      updateButtons(null);
    }
  }

  async function extractError(response) {
    try {
      const data = await response.clone().json();
      if (data && typeof data === 'object' && data.detail) {
        return data.detail;
      }
    } catch (error) {
      /* ignore */
    }
    try {
      const text = await response.text();
      if (text) return text;
    } catch (error) {
      /* ignore */
    }
    return `HTTP ${response.status}`;
  }

  async function load(project) {
    if (!project) {
      applyStatus(null);
      return;
    }
    try {
      infoLabel.textContent = translate('integrationStatusUpdating', 'Updating status…');
      const response = await global.fetch(`/api/v1/admin/projects/${encodeURIComponent(project)}/vk`);
      if (!response.ok) {
        throw new Error(await extractError(response));
      }
      const data = await response.json();
      applyStatus(data);
      setMessage('', 0);
      if (tokenInput) tokenInput.value = '';
    } catch (error) {
      console.error('vk_status_failed', error);
      setMessage(error.message || translate('integrationStatusError', 'Status error'), 4500);
      applyStatus(null);
    }
  }

  function ensureProjectSelected() {
    const name = projectName();
    if (!name) {
      setMessage(translate('projectsSelectProject', 'Select a project'), 3500);
      updateButtons(null);
      return null;
    }
    return name;
  }

  async function send(endpoint, payload, successMessage) {
    const project = ensureProjectSelected();
    if (!project) return;
    busy = true;
    updateButtons(lastStatus);
    setMessage(translate('integrationActionInProgress', 'Working…'), 0);
    try {
      const response = await global.fetch(
        `/api/v1/admin/projects/${encodeURIComponent(project)}${endpoint}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      );
      if (!response.ok) {
        throw new Error(await extractError(response));
      }
      const data = await response.json();
      applyStatus(data);
      setMessage(successMessage, UPDATE_DELAY_MS);
      if (tokenInput) tokenInput.value = '';
    } catch (error) {
      console.error('vk_action_failed', error);
      setMessage(error.message || translate('integrationActionFailed', 'Action failed'), 6000);
    } finally {
      busy = false;
      updateButtons(lastStatus);
    }
  }

  if (saveButton) {
    saveButton.addEventListener('click', () => {
      const payload = {
        auto_start: autoStartInput ? !!autoStartInput.checked : false,
        token: tokenInput ? tokenInput.value : '',
      };
      send('/vk/config', payload, translate('projectsSaved', 'Saved'));
    });
  }

  if (startButton) {
    startButton.addEventListener('click', () => {
      const payload = {
        auto_start: autoStartInput ? !!autoStartInput.checked : false,
      };
      const token = tokenInput ? tokenInput.value.trim() : '';
      if (token) {
        payload.token = token;
      }
      send('/vk/start', payload, translate('integrationActionStarted', 'Started'));
    });
  }

  if (stopButton) {
    stopButton.addEventListener('click', () => {
      const payload = {
        auto_start: autoStartInput ? !!autoStartInput.checked : false,
      };
      send('/vk/stop', payload, translate('integrationActionStopped', 'Stopped'));
    });
  }

  function handleLanguageApplied() {
    updatePlaceholder(lastStatus);
    applyStatus(lastStatus);
    if (!lastStatus) {
      infoLabel.textContent = buildInfo(null);
    }
  }

  registry.vk = {
    reset,
    applyProject,
    load,
    handleLanguageApplied,
  };

  reset();
})(window);
