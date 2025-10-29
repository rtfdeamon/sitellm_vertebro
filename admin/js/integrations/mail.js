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

  function refreshHint() {
    const enabled = enabledInput ? !!enabledInput.checked : false;
    const hasImap = Boolean(imapHostInput?.value.trim());
    const hasSmtp = Boolean(smtpHostInput?.value.trim());
    if (!hasImap && !hasSmtp) {
      hintLabel.textContent = tl('Укажите параметры IMAP/SMTP, чтобы ассистент мог работать с почтой.');
      return;
    }
    if (enabled) {
      hintLabel.textContent = tl('Интеграция активна. Ассистент может отправлять и читать почту.');
      return;
    }
    hintLabel.textContent =
      tl('Параметры сохранены, но интеграция выключена. Включите переключатель, чтобы активировать почтовый коннектор.');
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
    passwordInput.placeholder = tl('Пароль');
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
    passwordInput.placeholder = project.mail_password_set ? tl('Пароль сохранён') : tl('Пароль');
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
