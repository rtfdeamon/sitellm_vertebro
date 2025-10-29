/**
 * Test helpers for admin panel tests
 */

/**
 * Load and parse admin panel HTML to extract inline functions
 */
export function loadAdminPanelDOM() {
  const fs = require('fs');
  const path = require('path');
  const htmlPath = path.join(__dirname, '../../index.html');
  const html = fs.readFileSync(htmlPath, 'utf-8');

  // Set up DOM
  document.documentElement.innerHTML = html;

  // Execute inline scripts to make functions available
  const scripts = document.querySelectorAll('script:not([src])');
  scripts.forEach(script => {
    try {
      eval(script.textContent);
    } catch (e) {
      // Some scripts may fail in test environment, that's ok
    }
  });
}

/**
 * Mock fetch for testing
 */
export function mockFetch(responses = {}) {
  global.fetch = vi.fn((url, options) => {
    const response = responses[url] || responses.default;

    if (!response) {
      return Promise.reject(new Error(`No mock response for ${url}`));
    }

    return Promise.resolve({
      ok: response.ok !== undefined ? response.ok : true,
      status: response.status || 200,
      json: () => Promise.resolve(response.data || {}),
      text: () => Promise.resolve(response.text || ''),
      headers: new Headers(response.headers || {})
    });
  });
}

/**
 * Create mock admin session
 */
export function mockAdminSession(overrides = {}) {
  return {
    username: 'testuser',
    is_super: true,
    projects: ['test'],
    ...overrides
  };
}

/**
 * Clean up test DOM
 */
export function cleanupDOM() {
  document.body.innerHTML = '';
  document.head.innerHTML = '';
}
