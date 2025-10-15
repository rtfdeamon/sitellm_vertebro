import { beforeEach } from 'vitest';

// Обеспечиваем изоляцию тестов: чистим DOM и хранилища
beforeEach(() => {
  document.body.innerHTML = '';
  document.head.innerHTML = '';
  window.localStorage?.clear?.();
  window.sessionStorage?.clear?.();
});
