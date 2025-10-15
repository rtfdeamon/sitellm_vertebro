import { describe, it, expect, beforeEach, vi } from 'vitest';

const createAuthDom = () => {
  const authModal = document.createElement('div');
  const authForm = document.createElement('form');
  const authUserInput = document.createElement('input');
  authUserInput.id = 'adminAuthUsername';
  const authPasswordInput = document.createElement('input');
  authPasswordInput.type = 'password';
  const authSubmitBtn = document.createElement('button');
  const authCancelBtn = document.createElement('button');
  const authError = document.createElement('div');
  const authHint = document.createElement('div');
  authHint.textContent = 'Login to localhost';
  const authMessage = document.createElement('div');

  authSubmitBtn.type = 'submit';
  authCancelBtn.type = 'button';

  authForm.appendChild(authUserInput);
  authForm.appendChild(authPasswordInput);
  authForm.appendChild(authSubmitBtn);
  authModal.appendChild(authForm);
  authModal.appendChild(authError);
  authModal.appendChild(authHint);
  authModal.appendChild(authMessage);

  document.body.appendChild(authModal);

  return {
    authModal,
    authForm,
    authUserInput,
    authPasswordInput,
    authSubmitBtn,
    authCancelBtn,
    authError,
    authHint,
    authMessage
  };
};

const initAuthModule = async () => {
  vi.resetModules();
  await import('../js/auth.js');
  return window.initAdminAuth({
    ...createAuthDom(),
    adminBaseKey: 'https://example.com',
    authHeaderSessionKey: 'test_admin_auth_header',
    authUserStorageKey: 'test_admin_auth_user'
  });
};

describe('initAdminAuth', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    document.body.innerHTML = '';
  });

  it('сохраняет и очищает логин администратора', async () => {
    const auth = await initAuthModule();
    auth.setStoredAdminUser('admin');
    expect(window.localStorage.getItem('test_admin_auth_user')).toBe('admin');
    auth.setStoredAdminUser('');
    expect(window.localStorage.getItem('test_admin_auth_user')).toBeNull();
  });

  it('управляет заголовком авторизации в sessionStorage', async () => {
    const auth = await initAuthModule();
    expect(auth.getAuthHeaderForBase('https://example.com')).toBeNull();
    auth.setAuthHeaderForBase('https://example.com', 'Basic abc');
    expect(auth.getAuthHeaderForBase('https://example.com')).toBe('Basic abc');
    expect(window.sessionStorage.getItem('test_admin_auth_header')).toBe('Basic abc');
    auth.clearAuthHeaderForBase('https://example.com');
    expect(auth.getAuthHeaderForBase('https://example.com')).toBeNull();
    expect(window.sessionStorage.getItem('test_admin_auth_header')).toBeNull();
  });

  it('закрывает модалку по нажатию Отмена при запросе авторизации', async () => {
    const elements = createAuthDom();
    vi.resetModules();
    await import('../js/auth.js');
    const auth = window.initAdminAuth({
      ...elements,
      adminBaseKey: 'https://example.com',
      authHeaderSessionKey: 'test_admin_auth_header',
      authUserStorageKey: 'test_admin_auth_user'
    });

    const requestPromise = auth.requestAdminAuth();
    expect(elements.authModal.dataset.visible).toBe('true');

    setTimeout(() => {
      elements.authCancelBtn.click();
    }, 0);

    const result = await requestPromise;
    expect(result).toBe(false);
    expect(elements.authModal.dataset.visible).toBe('false');
  });
});
