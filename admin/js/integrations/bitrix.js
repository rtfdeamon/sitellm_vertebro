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
        console.warn('bitrix_translate_failed', error);
      }
    }
    if (fallback) {
      return formatTemplate(fallback, params);
    }
    return key;
  };

  function refreshHint() {
    const hasWebhook = Boolean(webhookInput.value.trim());
    if (!hasWebhook) {
      hintLabel.textContent = translate('integrationBitrixWebhookHint', 'Webhook is used for model requests and is stored on the server.');
      return;
    }
    if (enabledInput.checked) {
      hintLabel.textContent = translate('integrationBitrixActive', 'Integration is active. The model will be able to query Bitrix24.');
    } else {
      hintLabel.textContent = translate('integrationBitrixConfiguredButDisabled', 'Webhook saved, but integration is disabled. Enable the toggle to use Bitrix.');
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
