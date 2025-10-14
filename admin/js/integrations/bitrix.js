(function (global) {
  const registry = (global.ProjectIntegrations = global.ProjectIntegrations || {});

  const webhookInput = global.document.getElementById('projectBitrixWebhook');
  const enabledInput = global.document.getElementById('projectBitrixEnabled');
  const hintLabel = global.document.getElementById('projectBitrixHint');

  const hasElements = webhookInput && enabledInput && hintLabel;

  const fallback = {
    reset() {},
    applyProject() {},
    load() {},
  };

  if (!hasElements) {
    registry.bitrix = fallback;
    return;
  }

  function refreshHint() {
    const hasWebhook = Boolean(webhookInput.value.trim());
    if (!hasWebhook) {
      hintLabel.textContent = tl('Webhook используется для запросов модели и хранится на сервере.');
      return;
    }
    if (enabledInput.checked) {
      hintLabel.textContent = tl('Интеграция активна. Модель сможет запрашивать Bitrix24.');
    } else {
      hintLabel.textContent = tl('Webhook сохранён, но интеграция выключена. Включите переключатель, чтобы использовать Bitrix.');
    }
  }

  function applyProject(project) {
    enabledInput.checked = !!project?.bitrix_enabled;
    webhookInput.value = project?.bitrix_webhook_url || '';
    refreshHint();
  }

  function reset() {
    enabledInput.checked = false;
    webhookInput.value = '';
    refreshHint();
  }

  enabledInput.addEventListener('change', () => refreshHint());
  webhookInput.addEventListener('input', () => refreshHint());

  registry.bitrix = {
    reset,
    applyProject,
    load: () => {},
  };

  reset();
})(window);
