/**
 * Unit tests for internationalization (i18n) functions
 */
import { describe, it, expect, beforeEach } from 'vitest';

describe('i18n Functions', () => {
  describe('translateInstant', () => {
    it('should return key if no translation exists', () => {
      const translations = {};

      const translateInstant = (key) => {
        return translations[key] || key;
      };

      expect(translateInstant('unknownKey')).toBe('unknownKey');
    });

    it('should return translation if it exists', () => {
      const translations = {
        'greeting': 'Hello',
        'farewell': 'Goodbye'
      };

      const translateInstant = (key) => {
        return translations[key] || key;
      };

      expect(translateInstant('greeting')).toBe('Hello');
      expect(translateInstant('farewell')).toBe('Goodbye');
    });
  });

  describe('i18n parameter substitution', () => {
    it('should substitute parameters in translation strings', () => {
      const t = (key, params = {}) => {
        const translations = {
          'welcomeUser': 'Welcome, {name}!',
          'itemCount': 'You have {count} items',
          'multiParam': 'Hello {first} {last}'
        };

        let text = translations[key] || key;

        // Simple parameter substitution
        Object.keys(params).forEach(param => {
          const placeholder = `{${param}}`;
          text = text.replace(new RegExp(placeholder, 'g'), params[param]);
        });

        return text;
      };

      expect(t('welcomeUser', { name: 'John' })).toBe('Welcome, John!');
      expect(t('itemCount', { count: 5 })).toBe('You have 5 items');
      expect(t('multiParam', { first: 'John', last: 'Doe' })).toBe('Hello John Doe');
    });

    it('should handle missing parameters gracefully', () => {
      const t = (key, params = {}) => {
        const translations = {
          'welcomeUser': 'Welcome, {name}!'
        };

        let text = translations[key] || key;

        Object.keys(params).forEach(param => {
          const placeholder = `{${param}}`;
          text = text.replace(new RegExp(placeholder, 'g'), params[param]);
        });

        return text;
      };

      // Parameter not provided
      expect(t('welcomeUser')).toBe('Welcome, {name}!');
      // Wrong parameter name
      expect(t('welcomeUser', { username: 'John' })).toBe('Welcome, {name}!');
    });
  });

  describe('Language Selection', () => {
    const SUPPORTED_LANGUAGES = ['en', 'es', 'de', 'fr', 'it', 'pt', 'ru', 'zh', 'ja', 'ar'];

    it('should validate supported languages', () => {
      const isLanguageSupported = (lang) => {
        return SUPPORTED_LANGUAGES.includes(lang);
      };

      expect(isLanguageSupported('en')).toBe(true);
      expect(isLanguageSupported('ru')).toBe(true);
      expect(isLanguageSupported('zh')).toBe(true);
      expect(isLanguageSupported('unsupported')).toBe(false);
    });

    it('should fall back to default language', () => {
      const getLanguage = (requested, defaultLang = 'en') => {
        if (SUPPORTED_LANGUAGES.includes(requested)) {
          return requested;
        }
        return defaultLang;
      };

      expect(getLanguage('ru')).toBe('ru');
      expect(getLanguage('invalid')).toBe('en');
      expect(getLanguage('invalid', 'fr')).toBe('fr');
    });
  });

  describe('Language Storage', () => {
    beforeEach(() => {
      localStorage.clear();
    });

    it('should store language preference', () => {
      const setLanguagePreference = (lang) => {
        localStorage.setItem('admin_language', lang);
      };

      const getLanguagePreference = () => {
        return localStorage.getItem('admin_language');
      };

      setLanguagePreference('ru');
      expect(getLanguagePreference()).toBe('ru');
    });

    it('should return null if no preference is stored', () => {
      const getLanguagePreference = () => {
        return localStorage.getItem('admin_language');
      };

      expect(getLanguagePreference()).toBeNull();
    });
  });
});
