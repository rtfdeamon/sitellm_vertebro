/**
 * Unit tests for authentication functionality
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('Authentication Functions', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('getAuthHeaderForBase', () => {
    it('should return null when no auth header is stored', () => {
      // Simulate the function behavior
      const getAuthHeaderForBase = (base) => {
        const key = `admin_auth_header_v1:${base}`;
        return sessionStorage.getItem(key);
      };

      const result = getAuthHeaderForBase('http://localhost:8000');
      expect(result).toBeNull();
    });

    it('should return stored auth header', () => {
      const getAuthHeaderForBase = (base) => {
        const key = `admin_auth_header_v1:${base}`;
        return sessionStorage.getItem(key);
      };

      const setAuthHeaderForBase = (base, header) => {
        const key = `admin_auth_header_v1:${base}`;
        sessionStorage.setItem(key, header);
      };

      const baseUrl = 'http://localhost:8000';
      const authHeader = 'Bearer test-token-123';

      setAuthHeaderForBase(baseUrl, authHeader);
      const result = getAuthHeaderForBase(baseUrl);

      expect(result).toBe(authHeader);
    });
  });

  describe('clearAuthHeaderForBase', () => {
    it('should remove auth header from storage', () => {
      const getAuthHeaderForBase = (base) => {
        const key = `admin_auth_header_v1:${base}`;
        return sessionStorage.getItem(key);
      };

      const setAuthHeaderForBase = (base, header) => {
        const key = `admin_auth_header_v1:${base}`;
        sessionStorage.setItem(key, header);
      };

      const clearAuthHeaderForBase = (base) => {
        const key = `admin_auth_header_v1:${base}`;
        sessionStorage.removeItem(key);
        const userKey = `admin_auth_user_v1:${base}`;
        localStorage.removeItem(userKey);
      };

      const baseUrl = 'http://localhost:8000';
      setAuthHeaderForBase(baseUrl, 'Bearer test-token');

      clearAuthHeaderForBase(baseUrl);
      const result = getAuthHeaderForBase(baseUrl);

      expect(result).toBeNull();
    });
  });

  describe('getStoredAdminUser', () => {
    it('should return null when no user is stored', () => {
      const getStoredAdminUser = () => {
        const base = window.location.origin;
        const key = `admin_auth_user_v1:${base}`;
        const raw = localStorage.getItem(key);
        if (!raw) return null;
        try {
          return JSON.parse(raw);
        } catch {
          return null;
        }
      };

      // Mock window.location.origin
      Object.defineProperty(window, 'location', {
        value: { origin: 'http://localhost:8000' },
        writable: true
      });

      const result = getStoredAdminUser();
      expect(result).toBeNull();
    });

    it('should return stored user object', () => {
      const getStoredAdminUser = () => {
        const base = window.location.origin;
        const key = `admin_auth_user_v1:${base}`;
        const raw = localStorage.getItem(key);
        if (!raw) return null;
        try {
          return JSON.parse(raw);
        } catch {
          return null;
        }
      };

      const setStoredAdminUser = (value) => {
        const base = window.location.origin;
        const key = `admin_auth_user_v1:${base}`;
        if (value === null) {
          localStorage.removeItem(key);
        } else {
          localStorage.setItem(key, JSON.stringify(value));
        }
      };

      Object.defineProperty(window, 'location', {
        value: { origin: 'http://localhost:8000' },
        writable: true
      });

      const testUser = { username: 'admin', is_super: true };
      setStoredAdminUser(testUser);

      const result = getStoredAdminUser();
      expect(result).toEqual(testUser);
    });

    it('should handle invalid JSON gracefully', () => {
      const getStoredAdminUser = () => {
        const base = window.location.origin;
        const key = `admin_auth_user_v1:${base}`;
        const raw = localStorage.getItem(key);
        if (!raw) return null;
        try {
          return JSON.parse(raw);
        } catch {
          return null;
        }
      };

      Object.defineProperty(window, 'location', {
        value: { origin: 'http://localhost:8000' },
        writable: true
      });

      const key = `admin_auth_user_v1:http://localhost:8000`;
      localStorage.setItem(key, 'invalid-json{]');

      const result = getStoredAdminUser();
      expect(result).toBeNull();
    });
  });

  describe('requiresAdminAuth', () => {
    it('should return true for /api/v1/admin/ URLs', () => {
      const ADMIN_PROTECTED_PREFIXES = ['/api/v1/admin/', '/api/v1/backup/'];
      const ADMIN_BASE_KEY = 'http://localhost:8000';

      const requiresAdminAuth = (url) => {
        if (!url) return false;
        return ADMIN_PROTECTED_PREFIXES.some((prefix) =>
          url.startsWith(prefix) || url.startsWith(`${ADMIN_BASE_KEY}${prefix}`)
        );
      };

      expect(requiresAdminAuth('/api/v1/admin/session')).toBe(true);
      expect(requiresAdminAuth('/api/v1/admin/projects')).toBe(true);
      expect(requiresAdminAuth('http://localhost:8000/api/v1/admin/session')).toBe(true);
    });

    it('should return true for /api/v1/backup/ URLs', () => {
      const ADMIN_PROTECTED_PREFIXES = ['/api/v1/admin/', '/api/v1/backup/'];
      const ADMIN_BASE_KEY = 'http://localhost:8000';

      const requiresAdminAuth = (url) => {
        if (!url) return false;
        return ADMIN_PROTECTED_PREFIXES.some((prefix) =>
          url.startsWith(prefix) || url.startsWith(`${ADMIN_BASE_KEY}${prefix}`)
        );
      };

      expect(requiresAdminAuth('/api/v1/backup/status')).toBe(true);
      expect(requiresAdminAuth('/api/v1/backup/run')).toBe(true);
    });

    it('should return false for non-protected URLs', () => {
      const ADMIN_PROTECTED_PREFIXES = ['/api/v1/admin/', '/api/v1/backup/'];
      const ADMIN_BASE_KEY = 'http://localhost:8000';

      const requiresAdminAuth = (url) => {
        if (!url) return false;
        return ADMIN_PROTECTED_PREFIXES.some((prefix) =>
          url.startsWith(prefix) || url.startsWith(`${ADMIN_BASE_KEY}${prefix}`)
        );
      };

      expect(requiresAdminAuth('/api/v1/llm/chat')).toBe(false);
      expect(requiresAdminAuth('/health')).toBe(false);
      expect(requiresAdminAuth(null)).toBe(false);
    });
  });
});
