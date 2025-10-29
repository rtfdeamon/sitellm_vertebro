(function (global) {
  const registry = (global.ProjectIntegrations = global.ProjectIntegrations || {});

  const tokenInput = global.document.getElementById('projectTelegramToken');
  const autoStartInput = global.document.getElementById('projectTelegramAutoStart');
  const statusLabel = global.document.getElementById('projectTelegramStatus');
  const infoLabel = global.document.getElementById('projectTelegramInfo');
  const messageLabel = global.document.getElementById('projectTelegramMessage');
  const saveButton = global.document.getElementById('projectTelegramSave');
  const startButton = global.document.getElementById('projectTelegramStart');
  const stopButton = global.document.getElementById('projectTelegramStop');

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
    registry.telegram = fallback;
    return;
  }

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
      return tl('Выберите проект, чтобы управлять Telegram ботом.');
    }
    const parts = [];
    parts.push(status.token_set ? `Токен: ${status.token_preview || '••••'}` : tl('Токен не задан'));
    parts.push(`Автозапуск: ${status.auto_start ? tl('включён') : tl('выключен')}`);
    if (status.last_error) {
      parts.push(`Последняя ошибка: ${status.last_error}`);
    }
    return parts.join(' · ');
  }

  function updatePlaceholder(status) {
    if (!tokenInput) return;
    tokenInput.placeholder = status?.token_set ? tl('Токен сохранён') : tl('Введите токен');
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
    statusLabel.textContent = status.running ? tl('Запущен') : tl('Остановлен');
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
      tokenInput.placeholder = tl('Введите токен');
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
      autoStartInput.checked = !!project?.telegram_auto_start;
    }
    if (!project || !project.name) {
      applyStatus(null);
    } else if (!lastStatus) {
      infoLabel.textContent = tl('Сохраните токен и запустите бота.');
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
      infoLabel.textContent = tl('Обновляем статус…');
      const response = await global.fetch(`/api/v1/admin/projects/${encodeURIComponent(project)}/telegram`);
      if (!response.ok) {
        throw new Error(await extractError(response));
      }
      const data = await response.json();
      applyStatus(data);
      setMessage('', 0);
      if (tokenInput) tokenInput.value = '';
    } catch (error) {
      console.error('telegram_status_failed', error);
      setMessage(error.message || tl('Ошибка статуса'), 4500);
      applyStatus(null);
    }
  }

  function ensureProjectSelected() {
    const name = projectName();
    if (!name) {
      setMessage(tl('Выберите проект'), 3500);
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
    setMessage(tl('Выполняю…'), 0);
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
      console.error('telegram_action_failed', error);
      setMessage(error.message || tl('Ошибка действия'), 6000);
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
      send('/telegram/config', payload, tl('Сохранено'));
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
      send('/telegram/start', payload, tl('Запущено'));
    });
  }

  if (stopButton) {
    stopButton.addEventListener('click', () => {
      const payload = {
        auto_start: autoStartInput ? !!autoStartInput.checked : false,
      };
      send('/telegram/stop', payload, tl('Остановлено'));
    });
  }

  registry.telegram = {
    reset,
    applyProject,
    load,
  };

  reset();
})(window);
