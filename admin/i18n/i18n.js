/**
 * i18n - Internationalization module
 * Loads translations from JSON files and provides translation API
 *
 * Supported languages: en, ru (extensible)
 *
 * Usage:
 *   await i18n.init(['en', 'ru']);
 *   i18n.setLanguage('ru');
 *   const text = i18n.t('headerTitle');
 */

const i18n = (() => {
  const STORAGE_KEY = 'admin_language';
  const DEFAULT_LANGUAGE = 'en';

  let currentLanguage = DEFAULT_LANGUAGE;
  let languages = {};
  let loadedLanguages = new Set();

  /**
   * Load translation file for a specific language
   */
  async function loadLanguage(lang) {
    if (loadedLanguages.has(lang)) {
      return languages[lang];
    }

    try {
      const response = await fetch(`./i18n/${lang}.json`);
      if (!response.ok) {
        throw new Error(`Failed to load ${lang}.json: ${response.statusText}`);
      }

      const data = await response.json();
      languages[lang] = data;
      loadedLanguages.add(lang);

      return data;
    } catch (error) {
      console.error(`Error loading language ${lang}:`, error);
      return null;
    }
  }

  /**
   * Initialize i18n with list of supported languages
   */
  async function init(supportedLanguages = ['en', 'ru']) {
    // Load all language files
    await Promise.all(supportedLanguages.map(lang => loadLanguage(lang)));

    // Restore saved language from localStorage
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && languages[saved]) {
        currentLanguage = saved;
      }
    } catch (e) {
      console.warn('Could not access localStorage:', e);
    }

    return languages;
  }

  /**
   * Get translation for a key with optional parameter substitution
   * @param {string} key - Translation key
   * @param {object} params - Parameters to substitute (e.g., {value: '123'})
   * @returns {string} Translated text
   */
  function t(key, params = {}) {
    const currentLang = languages[currentLanguage];
    const defaultLang = languages[DEFAULT_LANGUAGE];

    let template = currentLang?.strings?.[key]
                || defaultLang?.strings?.[key]
                || key;

    // Replace parameters like {value}, {message}, etc.
    Object.entries(params).forEach(([paramKey, paramValue]) => {
      template = template.replace(`{${paramKey}}`, paramValue);
    });

    return template;
  }

  /**
   * Set current language
   */
  function setLanguage(lang) {
    if (!languages[lang]) {
      console.warn(`Language ${lang} not loaded, falling back to ${DEFAULT_LANGUAGE}`);
      lang = DEFAULT_LANGUAGE;
    }

    currentLanguage = lang;

    // Save to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, currentLanguage);
    } catch (e) {
      console.warn('Could not save language to localStorage:', e);
    }
  }

  /**
   * Get current language code
   */
  function getLanguage() {
    return currentLanguage;
  }

  /**
   * Get all loaded languages
   */
  function getLanguages() {
    return languages;
  }

  /**
   * Get language metadata (name, direction)
   */
  function getLanguageMetadata(lang) {
    const data = languages[lang || currentLanguage];
    return {
      name: data?.name || lang,
      dir: data?.dir || 'ltr'
    };
  }

  return {
    init,
    t,
    setLanguage,
    getLanguage,
    getLanguages,
    getLanguageMetadata,
    loadLanguage
  };
})();

// Export for use in HTML
if (typeof window !== 'undefined') {
  window.i18n = i18n;
}
