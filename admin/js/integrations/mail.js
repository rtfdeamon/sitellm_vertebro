(function (global) {
  const registry = (global.ProjectIntegrations = global.ProjectIntegrations || {});

  const enabledInput = global.document.getElementById('projectMailEnabled');
  const hintLabel = global.document.getElementById('projectMailHint');
  const imapHostInput = global.document.getElementById('projectMailImapHost');
  const imapPortInput = global.document.getElementById('projectMailImapPort');
  const imapSslInput = global.document.getElementById('projectMailImapSsl');
  const smtpHostInput = global.document.getElementById('projectMailSmtpHost');
  const smtpPortInput = global.document.getElementById('projectMailSmtpPort');
  const smtpTlsInput = global.document.getElementById('projectMailSmtpTls');
  const usernameInput = global.document.getElementById('projectMailUsername');
  const passwordInput = global.document.getElementById('projectMailPassword');
  const fromInput = global.document.getElementById('projectMailFrom');
  const signatureInput = global.document.getElementById('projectMailSignature');

  const hasElements =
    hintLabel &&
    enabledInput &&
    imapHostInput &&
    imapPortInput &&
    imapSslInput &&
    smtpHostInput &&
    smtpPortInput &&
    smtpTlsInput &&
    usernameInput &&
    passwordInput &&
    fromInput &&
    signatureInput;

  const fallback = {
    reset() {},
    applyProject() {},
    load() {},
  };

  if (!hasElements) {
    registry.mail = fallback;
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
        console.warn('mail_translate_failed', error);
      }
    }
    if (fallback) {
      return formatTemplate(fallback, params);
    }
    return key;
  };

  function refreshHint() {
    const enabled = enabledInput ? !!enabledInput.checked : false;
    const hasImap = Boolean(imapHostInput?.value.trim());
    const hasSmtp = Boolean(smtpHostInput?.value.trim());
    if (!hasImap && !hasSmtp) {
      hintLabel.textContent = translate('integrationMailHintNotConfigured', 'Specify IMAP/SMTP parameters so the assistant can work with email.');
      return;
    }
    if (enabled) {
      hintLabel.textContent = translate('integrationMailHintActive', 'Integration is active. The assistant can send and read emails.');
      return;
    }
    hintLabel.textContent =
      translate('integrationMailHintConfiguredButDisabled', 'Parameters saved, but integration is disabled. Enable the toggle to activate the mail connector.');
  }

  function resetInputs() {
    enabledInput.checked = false;
    imapHostInput.value = '';
    imapPortInput.value = '';
    imapSslInput.checked = true;
    smtpHostInput.value = '';
    smtpPortInput.value = '';
    smtpTlsInput.checked = true;
    usernameInput.value = '';
    passwordInput.value = '';
    passwordInput.placeholder = translate('integrationMailPassword', 'Password');
    fromInput.value = '';
    signatureInput.value = '';
  }

  function applyProject(project) {
    if (!project) {
      resetInputs();
      refreshHint();
      return;
    }
    enabledInput.checked = !!project.mail_enabled;
    imapHostInput.value = project.mail_imap_host || '';
    imapPortInput.value = project.mail_imap_port != null ? project.mail_imap_port : '';
    imapSslInput.checked = project.mail_imap_ssl !== false;
    smtpHostInput.value = project.mail_smtp_host || '';
    smtpPortInput.value = project.mail_smtp_port != null ? project.mail_smtp_port : '';
    smtpTlsInput.checked = project.mail_smtp_tls !== false;
    usernameInput.value = project.mail_username || '';
    passwordInput.value = '';
    passwordInput.placeholder = project.mail_password_set ? translate('integrationMailPasswordSaved', 'Password saved') : translate('integrationMailPassword', 'Password');
    fromInput.value = project.mail_from || '';
    signatureInput.value = project.mail_signature || '';
    refreshHint();
  }

  function reset() {
    resetInputs();
    refreshHint();
  }

  if (enabledInput) {
    enabledInput.addEventListener('change', () => refreshHint());
  }

  [imapHostInput, smtpHostInput].forEach((input) => {
    input.addEventListener('input', () => refreshHint());
  });

  registry.mail = {
    reset,
    applyProject,
    load: () => {},
  };

  reset();
})(window);
