import { beforeEach } from 'vitest';

// Сбрасываем DOM и хранилища перед каждым тестом
beforeEach(() => {
  document.body.innerHTML = '';
  document.head.innerHTML = '';
  window.localStorage?.clear?.();
  window.sessionStorage?.clear?.();
});
