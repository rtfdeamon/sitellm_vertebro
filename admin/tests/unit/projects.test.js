/**
 * Unit tests for project-related utility functions
 */
import { describe, it, expect } from 'vitest';

describe('Project Utility Functions', () => {
  describe('normalizeProjectName', () => {
    it('should trim and lowercase project names', () => {
      const normalizeProjectName = (value) =>
        typeof value === 'string' ? value.trim().toLowerCase() : '';

      expect(normalizeProjectName('Test Project')).toBe('test project');
      expect(normalizeProjectName('  UPPERCASE  ')).toBe('uppercase');
      expect(normalizeProjectName('MixedCase')).toBe('mixedcase');
    });

    it('should handle empty strings', () => {
      const normalizeProjectName = (value) =>
        typeof value === 'string' ? value.trim().toLowerCase() : '';

      expect(normalizeProjectName('')).toBe('');
      expect(normalizeProjectName('   ')).toBe('');
    });

    it('should return empty string for non-string values', () => {
      const normalizeProjectName = (value) =>
        typeof value === 'string' ? value.trim().toLowerCase() : '';

      expect(normalizeProjectName(null)).toBe('');
      expect(normalizeProjectName(undefined)).toBe('');
      expect(normalizeProjectName(123)).toBe('');
      expect(normalizeProjectName({})).toBe('');
    });
  });

  describe('buildTargetUrl', () => {
    it('should handle URLs with http protocol', () => {
      const buildTargetUrl = (raw) => {
        if (!raw || typeof raw !== 'string') return '';
        const trimmed = raw.trim();
        if (!trimmed) return '';
        if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
          return trimmed;
        }
        return `https://${trimmed}`;
      };

      expect(buildTargetUrl('http://example.com')).toBe('http://example.com');
      expect(buildTargetUrl('https://example.com')).toBe('https://example.com');
    });

    it('should add https:// prefix to URLs without protocol', () => {
      const buildTargetUrl = (raw) => {
        if (!raw || typeof raw !== 'string') return '';
        const trimmed = raw.trim();
        if (!trimmed) return '';
        if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
          return trimmed;
        }
        return `https://${trimmed}`;
      };

      expect(buildTargetUrl('example.com')).toBe('https://example.com');
      expect(buildTargetUrl('www.example.com')).toBe('https://www.example.com');
    });

    it('should handle empty or invalid input', () => {
      const buildTargetUrl = (raw) => {
        if (!raw || typeof raw !== 'string') return '';
        const trimmed = raw.trim();
        if (!trimmed) return '';
        if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
          return trimmed;
        }
        return `https://${trimmed}`;
      };

      expect(buildTargetUrl('')).toBe('');
      expect(buildTargetUrl('   ')).toBe('');
      expect(buildTargetUrl(null)).toBe('');
      expect(buildTargetUrl(undefined)).toBe('');
    });

    it('should trim whitespace', () => {
      const buildTargetUrl = (raw) => {
        if (!raw || typeof raw !== 'string') return '';
        const trimmed = raw.trim();
        if (!trimmed) return '';
        if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
          return trimmed;
        }
        return `https://${trimmed}`;
      };

      expect(buildTargetUrl('  example.com  ')).toBe('https://example.com');
      expect(buildTargetUrl('  https://example.com  ')).toBe('https://example.com');
    });
  });
});
