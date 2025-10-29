import { describe, it, expect, beforeEach, vi } from 'vitest';

const MAIL_HINT_DEFAULT = 'Укажите параметры IMAP/SMTP, чтобы ассистент мог работать с почтой.';
const MAIL_HINT_ENABLED = 'Интеграция активна. Ассистент может отправлять и читать почту.';
const MAIL_HINT_DISABLED =
  'Параметры сохранены, но интеграция выключена. Включите переключатель, чтобы активировать почтовый коннектор.';

const setupMailDom = () => {
  document.body.innerHTML = `
    <div>
      <input type="checkbox" id="projectMailEnabled">
      <span id="projectMailHint"></span>
      <input type="text" id="projectMailImapHost">
      <input type="number" id="projectMailImapPort">
      <input type="checkbox" id="projectMailImapSsl">
      <input type="text" id="projectMailSmtpHost">
      <input type="number" id="projectMailSmtpPort">
      <input type="checkbox" id="projectMailSmtpTls">
      <input type="text" id="projectMailUsername">
      <input type="password" id="projectMailPassword">
      <input type="email" id="projectMailFrom">
      <textarea id="projectMailSignature"></textarea>
    </div>
  `;
};

const elements = () => ({
  enabled: document.getElementById('projectMailEnabled'),
  hint: document.getElementById('projectMailHint'),
  imapHost: document.getElementById('projectMailImapHost'),
  imapPort: document.getElementById('projectMailImapPort'),
  imapSsl: document.getElementById('projectMailImapSsl'),
  smtpHost: document.getElementById('projectMailSmtpHost'),
  smtpPort: document.getElementById('projectMailSmtpPort'),
  smtpTls: document.getElementById('projectMailSmtpTls'),
  username: document.getElementById('projectMailUsername'),
  password: document.getElementById('projectMailPassword'),
  from: document.getElementById('projectMailFrom'),
  signature: document.getElementById('projectMailSignature'),
});

const loadModule = async () => {
  await import('../js/integrations/mail.js');
  return window.ProjectIntegrations.mail;
};

describe('Mail connector integration', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    setupMailDom();
    vi.stubGlobal('t', (key) => key);
    vi.stubGlobal('tl', (phrase) => phrase);
    window.ProjectIntegrations = {};
  });

  it('сбрасывает поля к значениям по умолчанию', async () => {
    const mail = await loadModule();
    const { enabled, hint, imapHost, imapPort, imapSsl, smtpHost, smtpPort, smtpTls, username, password, from, signature } =
      elements();

    enabled.checked = true;
    hint.textContent = '';
    imapHost.value = 'imap-set';
    imapPort.value = '111';
    imapSsl.checked = false;
    smtpHost.value = 'smtp-set';
    smtpPort.value = '222';
    smtpTls.checked = false;
    username.value = 'user-set';
    password.value = 'secret';
    password.placeholder = 'other';
    from.value = 'from-set@example.com';
    signature.value = 'signature';

    mail.reset();

    expect(enabled.checked).toBe(false);
    expect(imapHost.value).toBe('');
    expect(imapPort.value).toBe('');
    expect(imapSsl.checked).toBe(true);
    expect(smtpHost.value).toBe('');
    expect(smtpPort.value).toBe('');
    expect(smtpTls.checked).toBe(true);
    expect(username.value).toBe('');
    expect(password.value).toBe('');
    expect(password.placeholder).toBe('Пароль');
    expect(from.value).toBe('');
    expect(signature.value).toBe('');
    expect(hint.textContent).toBe(MAIL_HINT_DEFAULT);
  });

  it('применяет значения проекта и обновляет подсказку', async () => {
    const mail = await loadModule();
    const { enabled, hint, imapHost, imapPort, imapSsl, smtpHost, smtpPort, smtpTls, username, password, from, signature } =
      elements();

    mail.applyProject({
      mail_enabled: true,
      mail_imap_host: 'imap.example.com',
      mail_imap_port: 993,
      mail_imap_ssl: true,
      mail_smtp_host: 'smtp.example.com',
      mail_smtp_port: 587,
      mail_smtp_tls: false,
      mail_username: 'mailer',
      mail_from: 'robot@example.com',
      mail_signature: 'Regards, Bot',
      mail_password_set: true,
    });

    expect(enabled.checked).toBe(true);
    expect(imapHost.value).toBe('imap.example.com');
    expect(imapPort.value).toBe('993');
    expect(imapSsl.checked).toBe(true);
    expect(smtpHost.value).toBe('smtp.example.com');
    expect(smtpPort.value).toBe('587');
    expect(smtpTls.checked).toBe(false);
    expect(username.value).toBe('mailer');
    expect(from.value).toBe('robot@example.com');
    expect(signature.value).toBe('Regards, Bot');
    expect(password.value).toBe('');
    expect(password.placeholder).toBe('Пароль сохранён');
    expect(hint.textContent).toBe(MAIL_HINT_ENABLED);
  });

  it('показывает корректные подсказки при выключенной интеграции и пустых хостах', async () => {
    const mail = await loadModule();
    const { enabled, hint, imapHost, smtpHost } = elements();

    mail.applyProject({
      mail_enabled: false,
      mail_imap_host: 'imap.example.com',
      mail_smtp_host: '',
      mail_password_set: false,
    });

    expect(enabled.checked).toBe(false);
    expect(hint.textContent).toBe(MAIL_HINT_DISABLED);

    imapHost.value = '';
    imapHost.dispatchEvent(new Event('input'));

    expect(hint.textContent).toBe(MAIL_HINT_DEFAULT);

    smtpHost.value = 'smtp.example.com';
    smtpHost.dispatchEvent(new Event('input'));

    expect(hint.textContent).toBe(MAIL_HINT_DISABLED);
  });
});
