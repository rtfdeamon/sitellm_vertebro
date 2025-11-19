(function (global) {
  function initAdminAuth({
    authModal,
    authForm,
    authUserInput,
    authPasswordInput,
    authSubmitBtn,
    authCancelBtn,
    authError,
    authHint,
    authMessage,
    adminBaseKey = global.location.origin.replace(/\/$/, ''),
    authHeaderSessionKey = 'admin_auth_header_v1',
    authUserStorageKey = 'admin_auth_user_v1',
    authCancelledCode = 'ADMIN_AUTH_CANCELLED',
    protectedPrefixes = [
      '/api/v1/admin/',
      '/api/v1/backup/',
      '/api/v1/crawler/',
      '/api/intelligent-processing/'
    ],
  } = {}) {
    const nativeFetch = global.fetch.bind(global);
    const adminAuthHeaders = new Map();

    // Try to restore from sessionStorage first
    try {
      const storedHeader = global.sessionStorage?.getItem(authHeaderSessionKey);
      if (storedHeader) {
        adminAuthHeaders.set(adminBaseKey, storedHeader);
      }
    } catch (error) {
      console.warn('admin_auth_header_restore_failed', error);
    }

    // If no stored header, try to extract credentials from URL (HTTP Basic Auth)
    if (!adminAuthHeaders.has(adminBaseKey)) {
      try {
        const url = new URL(global.location.href);
        const username = url.username;
        const password = url.password;

        if (username && password) {
          // Encode credentials inline (same logic as encodeBasicAuth function)
          const raw = `${username}:${password}`;
          let token = null;
          try {
            token = global.btoa(raw);
          } catch (encError) {
            try {
              token = global.btoa(unescape(encodeURIComponent(raw)));
            } catch (fallbackError) {
              console.warn('admin_auth_base64_failed', fallbackError);
            }
          }

          if (token) {
            const header = `Basic ${token}`;
            adminAuthHeaders.set(adminBaseKey, header);
            // Store for future use
            try {
              global.sessionStorage?.setItem(authHeaderSessionKey, header);
            } catch (storageError) {
              console.warn('admin_auth_header_store_failed', storageError);
            }
            console.log('admin_auth_extracted_from_url');
          }
        }
      } catch (error) {
        console.warn('admin_auth_url_extraction_failed', error);
      }
    }

    if (authHint) {
      authHint.dataset.host = global.location.origin;
      authHint.textContent = authHint.textContent.replace('localhost', global.location.origin);
    }

    function translateInstant(key) {
      if (!key) return '';
      try {
        return typeof global.t === 'function' ? global.t(key) : key;
      } catch (error) {
        return key;
      }
    }

    function getAuthHeaderForBase(base) {
      return adminAuthHeaders.get(base) || null;
    }

    function setAuthHeaderForBase(base, header) {
      if (!header) {
        clearAuthHeaderForBase(base);
        return;
      }
      adminAuthHeaders.set(base, header);
      try {
        global.sessionStorage?.setItem(authHeaderSessionKey, header);
      } catch (error) {
        console.warn('admin_auth_header_store_failed', error);
      }
    }

    function clearAuthHeaderForBase(base) {
      adminAuthHeaders.delete(base);
      try {
        global.sessionStorage?.removeItem(authHeaderSessionKey);
      } catch (error) {
        console.warn('admin_auth_header_clear_failed', error);
      }
    }

    function getStoredAdminUser() {
      try {
        return global.localStorage?.getItem(authUserStorageKey) || '';
      } catch (error) {
        console.warn('admin_auth_user_restore_failed', error);
        return '';
      }
    }

    function setStoredAdminUser(value) {
      try {
        if (value) {
          global.localStorage?.setItem(authUserStorageKey, value);
        } else {
          global.localStorage?.removeItem(authUserStorageKey);
        }
      } catch (error) {
        console.warn('admin_auth_user_store_failed', error);
      }
    }

    function setAuthErrorKey(key) {
      if (!authError) return;
      if (key) {
        authError.dataset.key = key;
        authError.textContent = translateInstant(key);
      } else {
        delete authError.dataset.key;
        authError.textContent = '';
      }
    }

    function setAuthSubmitting(state) {
      if (authSubmitBtn) authSubmitBtn.disabled = state;
      if (authCancelBtn) authCancelBtn.disabled = state;
      if (state) {
        setAuthErrorKey('authStatusChecking');
      } else if (authError?.dataset.key === 'authStatusChecking') {
        setAuthErrorKey('');
      }
    }

    let authModalPromise = null;
    let authModalResolver = null;

    function showAuthModal() {
      if (!authModal) return;
      if (authModal.dataset.visible === 'true') return;
      setAuthSubmitting(false);
      setAuthErrorKey('');
      if (authMessage) authMessage.textContent = translateInstant('authPrompt');
      if (authHint) {
        const host = authHint.dataset.host || global.location.origin;
        authHint.textContent = translateInstant('authHint').replace('{host}', host);
      }
      if (authPasswordInput) authPasswordInput.value = '';
      const storedUser = getStoredAdminUser();
      if (authUserInput && !authUserInput.value && storedUser) {
        authUserInput.value = storedUser;
      }
      authModal.dataset.visible = 'true';
      global.document.body.classList.add('modal-open');
      global.setTimeout(() => {
        authUserInput?.focus();
        authUserInput?.select?.();
      }, 15);
    }

    function hideAuthModal() {
      if (!authModal) return;
      authModal.dataset.visible = 'false';
      global.document.body.classList.remove('modal-open');
      setAuthSubmitting(false);
    }

    function cancelAuthModal() {
      if (!authModal || authModal.dataset.visible !== 'true') return;
      hideAuthModal();
      setAuthErrorKey('');
      if (authModalResolver) authModalResolver(false);
    }

    async function verifyAdminCredentials(header) {
      try {
        const response = await nativeFetch('/api/v1/admin/session', {
          headers: { Authorization: header },
          credentials: 'same-origin',
        });
        return { ok: response.ok, status: response.status };
      } catch (error) {
        console.warn('admin_auth_verify_failed', error);
        return { ok: false, status: 0 };
      }
    }

    function requestAdminAuth() {
      // If no modal, assume HTTP Basic Auth credentials are already stored
      // Return true to allow retry with existing credentials from sessionStorage/URL
      if (!authModal) return Promise.resolve(true);
      if (authModalPromise) return authModalPromise;
      showAuthModal();
      authModalPromise = new Promise((resolve) => {
        authModalResolver = resolve;
      }).finally(() => {
        authModalPromise = null;
        authModalResolver = null;
      });
      return authModalPromise;
    }

    function createAuthCancelledError() {
      const error = new Error('admin-auth-cancelled');
      error.code = authCancelledCode;
      return error;
    }

    function encodeBasicAuth(username, password) {
      const raw = `${username}:${password}`;
      try {
        return global.btoa(raw);
      } catch (error) {
        try {
          return global.btoa(unescape(encodeURIComponent(raw)));
        } catch (fallbackError) {
          console.warn('admin_auth_base64_failed', fallbackError);
          return null;
        }
      }
    }

    async function handleAuthSubmit(event) {
      event.preventDefault();
      if (!authForm) return;
      const username = (authUserInput?.value || '').trim();
      const password = authPasswordInput?.value || '';
      if (!username || !password) {
        setAuthErrorKey('authErrorMissing');
        if (!username) authUserInput?.focus();
        else authPasswordInput?.focus();
        return;
      }
      const token = encodeBasicAuth(username, password);
      if (!token) {
        setAuthErrorKey('authErrorInvalid');
        return;
      }
      const header = `Basic ${token}`;
      setAuthSubmitting(true);
      const result = await verifyAdminCredentials(header);
      setAuthSubmitting(false);
      if (!result.ok) {
        if (result.status === 401) {
          setAuthErrorKey('authErrorInvalid');
          if (authPasswordInput) {
            authPasswordInput.value = '';
            authPasswordInput.focus();
          }
        } else {
          setAuthErrorKey('authErrorNetwork');
        }
        return;
      }
      setAuthHeaderForBase(adminBaseKey, header);
      setStoredAdminUser(username);
      if (authPasswordInput) authPasswordInput.value = '';
      hideAuthModal();
      setAuthErrorKey('');
      if (authModalResolver) authModalResolver(true);
    }

    if (authForm) {
      authForm.addEventListener('submit', handleAuthSubmit);
    }

    if (authCancelBtn) {
      authCancelBtn.addEventListener('click', (event) => {
        event.preventDefault();
        cancelAuthModal();
      });
    }

    if (authModal) {
      authModal.addEventListener('click', (event) => {
        if (event.target === authModal || event.target.classList.contains('auth-backdrop')) {
          event.preventDefault();
          cancelAuthModal();
        }
      });
    }

    global.document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && authModal?.dataset.visible === 'true') {
        event.preventDefault();
        event.stopImmediatePropagation();
        cancelAuthModal();
      }
    }, true);

    function requiresAdminAuth(url) {
      if (!url) return false;
      return protectedPrefixes.some((prefix) => url.startsWith(prefix) || url.startsWith(`${adminBaseKey}${prefix}`));
    }

    async function fetchAdmin(url, init = {}) {
      const attempt = async () => {
        const headers = new Headers(init.headers || {});
        const token = getAuthHeaderForBase(adminBaseKey);
        if (token && !headers.has('Authorization')) {
          headers.set('Authorization', token);
        }
        const options = { ...init, headers };
        if (!options.credentials) options.credentials = 'same-origin';
        return nativeFetch(url, options);
      };

      let response;
      try {
        response = await attempt();
      } catch (error) {
        throw error;
      }

      if (response.status !== 401) {
        if (response.status === 403) {
          clearAuthHeaderForBase(adminBaseKey);
        }
        return response;
      }

      const authenticated = await requestAdminAuth();
      if (!authenticated) {
        throw createAuthCancelledError();
      }

      response = await attempt();
      if (response.status === 401) {
        clearAuthHeaderForBase(adminBaseKey);
      }
      return response;
    }

    global.fetch = async function wrappedFetch(input, init = {}) {
      if (typeof input === 'string' && requiresAdminAuth(input)) {
        return fetchAdmin(input, init);
      }
      if (typeof input === 'string' && requiresAdminAuth(`${adminBaseKey}${input}`)) {
        return fetchAdmin(input, init);
      }
      return nativeFetch(input, init);
    };

    const api = {
      getAuthHeaderForBase,
      setAuthHeaderForBase,
      clearAuthHeaderForBase,
      setStoredAdminUser,
      requestAdminAuth,
    };

    global.AdminAuth = api;
    return api;
  }

  global.initAdminAuth = initAdminAuth;
})(window);
