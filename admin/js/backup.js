(function (global) {
  const backupEnabledInput = document.getElementById('backupEnabled');
  const backupTimeInput = document.getElementById('backupTime');
  const backupTimezoneSelect = document.getElementById('backupTimezone');
  const backupFolderInput = document.getElementById('backupFolder');
  const backupTokenInput = document.getElementById('backupToken');
  const backupTokenSaveBtn = document.getElementById('backupTokenSave');
  const backupTokenClearBtn = document.getElementById('backupTokenClear');
  const backupTokenStatus = document.getElementById('backupTokenStatus');
  const backupSettingsApplyBtn = document.getElementById('backupSettingsApply');
  const backupStatusLine = document.getElementById('backupStatusLine');
  const backupRunBtn = document.getElementById('backupRunBtn');
  const backupRefreshBtn = document.getElementById('backupRefreshBtn');
  const backupRestorePathInput = document.getElementById('backupRestorePath');
  const backupRestoreBtn = document.getElementById('backupRestoreBtn');
  const backupJobsList = document.getElementById('backupJobsList');
  const backupErrorLine = document.getElementById('backupErrorLine');
  const backupCard = document.getElementById('block-backup');

  const BACKUP_TIMEZONES = [
    'UTC',
    'Europe/Kaliningrad',
    'Europe/Moscow',
    'Europe/Samara',
    'Asia/Yekaterinburg',
    'Asia/Omsk',
    'Asia/Novosibirsk',
    'Asia/Krasnoyarsk',
    'Asia/Irkutsk',
    'Asia/Yakutsk',
    'Asia/Vladivostok',
    'Asia/Sakhalin',
    'Asia/Magadan',
    'Asia/Kamchatka',
  ];

  let backupState = null;
  let backupUnavailable = false;
  let backupRefreshTimer = null;
  let listenersBound = false;

  const translate = (key, params) => {
    if (typeof global.t === 'function') {
      try {
        return global.t(key, params);
      } catch (error) {
        console.warn('backup_translate_failed', error);
      }
    }
    if (params && typeof params.value === 'string') {
      return `${key}: ${params.value}`;
    }
    return key || '';
  };

  const ensureBackupTimezones = () => {
    if (!backupTimezoneSelect || backupTimezoneSelect.options.length) return;
    BACKUP_TIMEZONES.forEach((tz) => {
      const option = document.createElement('option');
      option.value = tz;
      option.textContent = tz;
      backupTimezoneSelect.appendChild(option);
    });
  };

  const setBackupControlsDisabled = (disabled) => {
    [
      backupEnabledInput,
      backupTimeInput,
      backupTimezoneSelect,
      backupFolderInput,
      backupTokenInput,
      backupTokenSaveBtn,
      backupTokenClearBtn,
      backupSettingsApplyBtn,
      backupRunBtn,
      backupRefreshBtn,
      backupRestorePathInput,
      backupRestoreBtn,
    ].forEach((node) => {
      if (node) node.disabled = disabled;
    });
  };

  const formatBackupTimeValue = (hour, minute) => {
    const safeHour = Math.max(0, Math.min(23, Number.isFinite(Number(hour)) ? Number(hour) : 0));
    const safeMinute = Math.max(0, Math.min(59, Number.isFinite(Number(minute)) ? Number(minute) : 0));
    return `${String(safeHour).padStart(2, '0')}:${String(safeMinute).padStart(2, '0')}`;
  };

  const parseBackupTime = (value) => {
    if (typeof value !== 'string') return { hour: 3, minute: 0 };
    const [hours, minutes] = value.split(':');
    const hour = Number(hours);
    const minute = Number(minutes);
    if (!Number.isFinite(hour) || !Number.isFinite(minute)) {
      return { hour: 3, minute: 0 };
    }
    return {
      hour: Math.max(0, Math.min(23, Math.trunc(hour))),
      minute: Math.max(0, Math.min(59, Math.trunc(minute))),
    };
  };

  const formatBackupTimestamp = (value) => {
    if (!value) return null;
    try {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return null;
      return date.toLocaleString();
    } catch (_) {
      return null;
    }
  };

  const pushBackupMessage = (key, type = 'info') => {
    if (!backupErrorLine) return;
    const message = key ? translate(key) : '';
    backupErrorLine.textContent = message;
    backupErrorLine.classList.remove('bad', 'ok');
    if (!message) return;
    if (type === 'error') {
      backupErrorLine.classList.add('bad');
    } else if (type === 'success') {
      backupErrorLine.classList.add('ok');
    }
  };

  const scheduleBackupRefresh = (active) => {
    if (backupRefreshTimer) {
      clearTimeout(backupRefreshTimer);
      backupRefreshTimer = null;
    }
    if (active) {
      backupRefreshTimer = setTimeout(() => {
        refreshBackupStatus(false);
      }, 5000);
    }
  };

  const updateBackupActionButtons = () => {
    const tokenSet = Boolean(backupState?.settings?.tokenSet);
    const activeJob = Boolean(backupState?.activeJob);
    const hasRestorePath = Boolean(backupRestorePathInput?.value.trim());
    const isSuper = Boolean(global.adminSession?.is_super);
    if (backupRunBtn) backupRunBtn.disabled = !isSuper || !tokenSet || activeJob;
    if (backupRefreshBtn) backupRefreshBtn.disabled = !isSuper;
    if (backupSettingsApplyBtn) backupSettingsApplyBtn.disabled = !isSuper;
    if (backupTokenSaveBtn) backupTokenSaveBtn.disabled = !isSuper;
    if (backupTokenClearBtn) backupTokenClearBtn.disabled = !isSuper;
    if (backupRestoreBtn) backupRestoreBtn.disabled = !isSuper || !tokenSet || activeJob || !hasRestorePath;
  };

  const renderBackupState = (data) => {
    if (!global.adminSession?.is_super) {
      scheduleBackupRefresh(false);
      return;
    }
    ensureBackupTimezones();
    backupState = {
      settings: data?.settings || {},
      activeJob: data?.activeJob || null,
      jobs: Array.isArray(data?.jobs) ? data.jobs : [],
    };
    const settings = backupState.settings;
    if (backupEnabledInput) {
      backupEnabledInput.checked = settings.enabled === undefined ? false : Boolean(settings.enabled);
    }
    if (backupTimeInput) {
      backupTimeInput.value = formatBackupTimeValue(settings.hour ?? 3, settings.minute ?? 0);
    }
    if (backupTimezoneSelect) {
      const tzValue = settings.timezone || 'UTC';
      if (!Array.from(backupTimezoneSelect.options).some((option) => option.value === tzValue)) {
        const option = document.createElement('option');
        option.value = tzValue;
        option.textContent = tzValue;
        backupTimezoneSelect.appendChild(option);
      }
      backupTimezoneSelect.value = tzValue;
    }
    if (backupFolderInput) {
      backupFolderInput.value = settings.yaDiskFolder || '';
    }
    if (backupTokenStatus) {
      if (settings.tokenSet) {
        backupTokenStatus.textContent = translate('backupTokenSaved');
        backupTokenStatus.classList.add('ok');
        backupTokenStatus.classList.remove('bad');
      } else {
        backupTokenStatus.textContent = translate('backupTokenMissing');
        backupTokenStatus.classList.add('bad');
        backupTokenStatus.classList.remove('ok');
      }
    }

    const lines = [];
    const activeJob = backupState.activeJob;
    if (activeJob) {
      const statusKey = activeJob.status === 'running' ? 'backupStatusLineActive' : 'backupStatusLineQueued';
      lines.push(translate(statusKey));
    } else if (!settings.enabled) {
      lines.push(translate('backupStatusLineWaiting'));
    }
    const lastRunText = formatBackupTimestamp(settings.lastRunAtIso || settings.lastRunAt);
    if (lastRunText) {
      lines.push(translate('backupStatusLastRun', { value: lastRunText }));
    }
    const lastSuccessText = formatBackupTimestamp(settings.lastSuccessAtIso || settings.lastSuccessAt);
    if (lastSuccessText) {
      lines.push(translate('backupStatusLastSuccess', { value: lastSuccessText }));
    }
    if (!lastRunText && !lastSuccessText && !activeJob) {
      lines.push(translate('backupStatusNever'));
    }
    if (backupStatusLine) {
      backupStatusLine.textContent = lines.join(' • ');
    }

    if (backupJobsList) {
      backupJobsList.innerHTML = '';
      const jobs = backupState.jobs;
      if (!jobs.length) {
        const empty = document.createElement('div');
        empty.className = 'backup-empty';
        empty.textContent = translate('backupJobsEmpty');
        backupJobsList.appendChild(empty);
      } else {
        jobs.forEach((job) => {
          const wrapper = document.createElement('div');
          wrapper.className = 'backup-job';
          if (activeJob && job.id === activeJob.id) {
            wrapper.classList.add('primary');
          }
          const operationLabel = job.operation === 'restore'
            ? translate('backupJobOperationRestore')
            : translate('backupJobOperationBackup');
          let statusKey = 'backupJobStatusQueued';
          if (job.status === 'running') statusKey = 'backupJobStatusRunning';
          else if (job.status === 'completed') statusKey = 'backupJobStatusCompleted';
          else if (job.status === 'failed') statusKey = 'backupJobStatusFailed';

          const title = document.createElement('strong');
          title.textContent = `${operationLabel} — ${translate(statusKey)}`;
          wrapper.appendChild(title);

          if (job.remotePath) {
            const remote = document.createElement('small');
            remote.textContent = job.remotePath;
            wrapper.appendChild(remote);
          }

          if (job.createdAtIso || job.createdAt) {
            const created = document.createElement('small');
            created.textContent = formatBackupTimestamp(job.createdAtIso || job.createdAt) || '';
            wrapper.appendChild(created);
          }

          if (job.error) {
            const errorRow = document.createElement('small');
            errorRow.className = 'bad';
            errorRow.textContent = job.error;
            wrapper.appendChild(errorRow);
          }

          if (job.remotePath) {
            const actions = document.createElement('div');
            actions.className = 'backup-job-actions';
            if (job.operation === 'backup' && backupRestorePathInput) {
              const useBtn = document.createElement('button');
              useBtn.type = 'button';
              useBtn.textContent = translate('backupJobRestore');
              useBtn.addEventListener('click', () => {
                backupRestorePathInput.value = job.remotePath;
                updateBackupActionButtons();
                backupRestorePathInput.focus();
              });
              actions.appendChild(useBtn);
            }
            const copyBtn = document.createElement('button');
            copyBtn.type = 'button';
            copyBtn.textContent = translate('backupJobCopyPath');
            copyBtn.addEventListener('click', async () => {
              try {
                if (navigator.clipboard?.writeText) {
                  await navigator.clipboard.writeText(job.remotePath);
                } else {
                  const temp = document.createElement('textarea');
                  temp.value = job.remotePath;
                  document.body.appendChild(temp);
                  temp.select();
                  document.execCommand('copy');
                  document.body.removeChild(temp);
                }
                pushBackupMessage('logCopySuccess', 'success');
              } catch (error) {
                console.error('backup_copy_path_failed', error);
                pushBackupMessage('logCopyError', 'error');
              }
            });
            actions.appendChild(copyBtn);
            wrapper.appendChild(actions);
          }

          backupJobsList.appendChild(wrapper);
        });
      }
    }

    updateBackupActionButtons();
    scheduleBackupRefresh(Boolean(activeJob));
  };

  const refreshBackupStatus = async (clearMessage = false) => {
    // Wait for session to be loaded before checking permissions
    if (!global.adminSession?.username) {
      // Session not loaded yet, retry after a short delay
      setTimeout(() => refreshBackupStatus(clearMessage), 100);
      return;
    }

    // Hide backup section entirely for non-super admins (security requirement)
    if (!global.adminSession?.is_super) {
      if (backupCard) backupCard.style.display = 'none';
      scheduleBackupRefresh(false);
      return;
    }

    if (backupUnavailable) {
      scheduleBackupRefresh(false);
      return;
    }
    ensureBackupTimezones();
    if (backupRefreshTimer) {
      clearTimeout(backupRefreshTimer);
      backupRefreshTimer = null;
    }
    try {
      const resp = await fetch('/api/v1/backup/status?limit=6', { credentials: 'same-origin' });
      if (resp.status === 401 || resp.status === 403 || resp.status === 404) {
        backupUnavailable = true;
        setBackupControlsDisabled(true);
        if (backupCard) backupCard.style.display = 'none';
        scheduleBackupRefresh(false);
        return;
      }
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const data = await resp.json();
      renderBackupState(data);
      if (clearMessage) pushBackupMessage('', 'info');
    } catch (error) {
      if (error && error.code === global.AUTH_CANCELLED_CODE) {
        backupUnavailable = true;
        setBackupControlsDisabled(true);
        if (backupCard) backupCard.style.display = 'none';
        scheduleBackupRefresh(false);
        return;
      }
      console.error('backup_status_failed', error);
      pushBackupMessage('backupJobsFetchError', 'error');
    }
  };

  const handleBackupSettingsSave = async ({ tokenAction } = {}) => {
    if (!global.adminSession?.is_super) return;
    ensureBackupTimezones();
    const { hour, minute } = parseBackupTime(backupTimeInput?.value || '03:00');
    const payload = {
      enabled: Boolean(backupEnabledInput?.checked),
      hour,
      minute,
      timezone: backupTimezoneSelect?.value || 'UTC',
      yaDiskFolder: backupFolderInput?.value?.trim() || 'sitellm-backups',
    };
    if (tokenAction === 'save') {
      const tokenValue = (backupTokenInput?.value || '').trim();
      if (!tokenValue) {
        pushBackupMessage('backupTokenRequired', 'error');
        return;
      }
      payload.token = tokenValue;
    } else if (tokenAction === 'clear') {
      payload.clearToken = true;
    }
    try {
      const resp = await fetch('/api/v1/backup/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      if (tokenAction === 'save' && backupTokenInput) {
        backupTokenInput.value = '';
      }
      pushBackupMessage('backupSaveSuccess', 'success');
      await refreshBackupStatus(false);
    } catch (error) {
      console.error('backup_settings_save_failed', error);
      pushBackupMessage('backupSaveError', 'error');
    }
  };

  const handleBackupRun = async () => {
    if (!global.adminSession?.is_super || backupRunBtn?.disabled) return;
    try {
      backupRunBtn.disabled = true;
      const resp = await fetch('/api/v1/backup/run', { method: 'POST', credentials: 'same-origin' });
      if (!resp.ok) {
        const detail = await resp.json().catch(() => null);
        throw new Error(detail?.detail || `HTTP ${resp.status}`);
      }
      pushBackupMessage('backupRunQueued', 'success');
      await refreshBackupStatus(false);
    } catch (error) {
      console.error('backup_run_failed', error);
      pushBackupMessage('backupSaveError', 'error');
    } finally {
      updateBackupActionButtons();
    }
  };

  const handleBackupRestore = async () => {
    if (!global.adminSession?.is_super || backupRestoreBtn?.disabled) return;
    const remotePath = (backupRestorePathInput?.value || '').trim();
    if (!remotePath) {
      pushBackupMessage('backupRestorePathMissing', 'error');
      return;
    }
    try {
      backupRestoreBtn.disabled = true;
      const resp = await fetch('/api/v1/backup/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ remotePath }),
      });
      if (!resp.ok) {
        const detail = await resp.json().catch(() => null);
        throw new Error(detail?.detail || `HTTP ${resp.status}`);
      }
      pushBackupMessage('backupRestoreQueued', 'success');
      await refreshBackupStatus(false);
    } catch (error) {
      console.error('backup_restore_failed', error);
      pushBackupMessage('backupSaveError', 'error');
    } finally {
      updateBackupActionButtons();
    }
  };

  const handleLanguageApplied = () => {
    if (backupState) {
      renderBackupState(backupState);
    } else if (backupJobsList) {
      backupJobsList.innerHTML = '';
      const empty = document.createElement('div');
      empty.className = 'backup-empty';
      empty.textContent = translate('backupJobsEmpty');
      backupJobsList.appendChild(empty);
    }
  };

  const bindListeners = () => {
    if (listenersBound) return;
    listenersBound = true;

    if (backupSettingsApplyBtn) {
      backupSettingsApplyBtn.addEventListener('click', () => handleBackupSettingsSave());
    }
    if (backupTokenSaveBtn) {
      backupTokenSaveBtn.addEventListener('click', () => handleBackupSettingsSave({ tokenAction: 'save' }));
    }
    if (backupTokenClearBtn) {
      backupTokenClearBtn.addEventListener('click', () => handleBackupSettingsSave({ tokenAction: 'clear' }));
    }
    if (backupRunBtn) {
      backupRunBtn.addEventListener('click', handleBackupRun);
    }
    if (backupRefreshBtn) {
      backupRefreshBtn.addEventListener('click', () => refreshBackupStatus(true));
    }
    if (backupRestoreBtn) {
      backupRestoreBtn.addEventListener('click', handleBackupRestore);
    }
    if (backupRestorePathInput) {
      backupRestorePathInput.addEventListener('input', () => updateBackupActionButtons());
    }
  };

  const init = () => {
    // Security: Hide backup section for non-super admins immediately
    // But only after session is loaded to avoid race condition
    if (global.adminSession?.username && !global.adminSession?.is_super) {
      if (backupCard) backupCard.style.display = 'none';
      return;
    }

    ensureBackupTimezones();
    setBackupControlsDisabled(true);
    updateBackupActionButtons();
    bindListeners();
    handleLanguageApplied();
    refreshBackupStatus(false);
  };

  const start = () => {
    if (global.BackupModule?.__initialized) return;
    init();
    global.BackupModule = {
      handleLanguageApplied,
      refreshBackupStatus,
      renderBackupState,
      updateBackupActionButtons,
      init,
      __initialized: true,
    };
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})(window);
