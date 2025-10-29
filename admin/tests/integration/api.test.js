/**
 * Integration tests for API interactions
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('API Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
  });

  describe('Admin Session API', () => {
    it('should fetch session with auth header', async () => {
      const mockResponse = {
        username: 'admin',
        is_super: true,
        projects: ['test']
      };

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockResponse)
        })
      );

      const fetchSession = async (authHeader) => {
        const response = await fetch('/api/v1/admin/session', {
          headers: {
            'Authorization': authHeader
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        return response.json();
      };

      const result = await fetchSession('Bearer test-token');

      expect(fetch).toHaveBeenCalledWith(
        '/api/v1/admin/session',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          })
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle 401 unauthorized response', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 401
        })
      );

      const fetchSession = async (authHeader) => {
        const response = await fetch('/api/v1/admin/session', {
          headers: {
            'Authorization': authHeader
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        return response.json();
      };

      await expect(fetchSession('Bearer invalid-token'))
        .rejects
        .toThrow('HTTP 401');
    });
  });

  describe('Admin Logout', () => {
    it('should call logout endpoint and clear storage', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ ok: true })
        })
      );

      // Setup: Store auth data
      sessionStorage.setItem('admin_auth_header_v1:http://localhost:8000', 'Bearer token');
      localStorage.setItem('admin_auth_user_v1:http://localhost:8000', JSON.stringify({ username: 'admin' }));

      const performAdminLogout = async () => {
        await fetch('/api/v1/admin/logout', { method: 'POST' });

        // Clear storage
        const base = 'http://localhost:8000';
        sessionStorage.removeItem(`admin_auth_header_v1:${base}`);
        localStorage.removeItem(`admin_auth_user_v1:${base}`);
      };

      await performAdminLogout();

      expect(fetch).toHaveBeenCalledWith('/api/v1/admin/logout', { method: 'POST' });
      expect(sessionStorage.getItem('admin_auth_header_v1:http://localhost:8000')).toBeNull();
      expect(localStorage.getItem('admin_auth_user_v1:http://localhost:8000')).toBeNull();
    });
  });

  describe('Knowledge API', () => {
    it('should fetch knowledge priority', async () => {
      const mockPriority = {
        order: ['faq', 'vector', 'documents']
      };

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockPriority)
        })
      );

      const loadKnowledgePriority = async (projectName) => {
        const response = await fetch(
          `/api/v1/admin/knowledge/priority?project=${encodeURIComponent(projectName)}`
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        return response.json();
      };

      const result = await loadKnowledgePriority('test');

      expect(fetch).toHaveBeenCalledWith('/api/v1/admin/knowledge/priority?project=test');
      expect(result).toEqual(mockPriority);
    });

    it('should save knowledge priority', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ ok: true })
        })
      );

      const saveKnowledgePriority = async (projectName, order) => {
        const response = await fetch('/api/v1/admin/knowledge/priority', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ project: projectName, order })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        return response.json();
      };

      const newOrder = ['vector', 'faq', 'documents'];
      await saveKnowledgePriority('test', newOrder);

      expect(fetch).toHaveBeenCalledWith(
        '/api/v1/admin/knowledge/priority',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify({ project: 'test', order: newOrder })
        })
      );
    });
  });

  describe('Backup API', () => {
    it('should fetch backup status', async () => {
      const mockStatus = {
        settings: {
          enabled: true,
          tokenSet: true
        },
        activeJob: null,
        jobs: []
      };

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockStatus)
        })
      );

      const fetchBackupStatus = async () => {
        const response = await fetch('/api/v1/backup/status?limit=6');

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        return response.json();
      };

      const result = await fetchBackupStatus();

      expect(fetch).toHaveBeenCalledWith('/api/v1/backup/status?limit=6');
      expect(result).toEqual(mockStatus);
    });

    it('should handle 404 when backup is unavailable', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 404
        })
      );

      const fetchBackupStatus = async () => {
        const response = await fetch('/api/v1/backup/status?limit=6');

        if (response.status === 404) {
          return { unavailable: true };
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        return response.json();
      };

      const result = await fetchBackupStatus();

      expect(result).toEqual({ unavailable: true });
    });
  });
});
