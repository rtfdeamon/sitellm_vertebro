/**
 * Theme Switcher for SiteLLM Vertebro Admin Panel
 * Handles theme selection, persistence, and system preference detection
 */

const THEMES = {
  DARK: 'dark',
  LIGHT: 'light',
  SAND: 'sand'
};

const STORAGE_KEY = 'sitellm-theme-preference';

class ThemeSwitcher {
  constructor() {
    this.currentTheme = this.loadTheme();
    this.init();
  }

  /**
   * Initialize theme switcher
   */
  init() {
    this.applyTheme(this.currentTheme);
    this.createSwitcher();
    this.setupListeners();
  }

  /**
   * Load saved theme from localStorage or detect system preference
   */
  loadTheme() {
    // Try localStorage first
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && Object.values(THEMES).includes(saved)) {
      return saved;
    }

    // Detect system preference
    if (window.matchMedia) {
      if (window.matchMedia('(prefers-color-scheme: light)').matches) {
        return THEMES.LIGHT;
      }
    }

    // Default to dark theme
    return THEMES.DARK;
  }

  /**
   * Apply theme to document
   */
  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    this.currentTheme = theme;
    localStorage.setItem(STORAGE_KEY, theme);
    
    // Update button states
    this.updateButtonStates();
    
    // Log theme change for debugging
    console.log(`[Theme] Applied theme: ${theme}`);
  }

  /**
   * Create theme switcher UI
   */
  createSwitcher() {
    const headerActions = document.querySelector('.page-header-actions');
    if (!headerActions) {
      console.warn('[Theme] Could not find .page-header-actions container');
      return;
    }

    // Check if already exists
    if (document.getElementById('themeSwitcher')) {
      return;
    }

    const switcher = document.createElement('div');
    switcher.id = 'themeSwitcher';
    switcher.className = 'theme-switcher';
    switcher.innerHTML = `
      <span class="theme-switcher-label" data-i18n="theme">Theme</span>
      <div class="theme-switcher-buttons">
        <button
          class="theme-button"
          data-theme="${THEMES.DARK}"
          data-i18n="themeDark"
          title="Dark theme"
        >Dark</button>
        <button
          class="theme-button"
          data-theme="${THEMES.LIGHT}"
          data-i18n="themeLight"
          title="Light theme"
        >Light</button>
        <button
          class="theme-button"
          data-theme="${THEMES.SAND}"
          data-i18n="themeSand"
          title="Sand theme"
        >Sand</button>
      </div>
    `;

    // Insert before language select (first child)
    const firstChild = headerActions.firstChild;
    headerActions.insertBefore(switcher, firstChild);

    // Update button states
    this.updateButtonStates();
  }

  /**
   * Update active state of theme buttons
   */
  updateButtonStates() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(button => {
      const theme = button.getAttribute('data-theme');
      if (theme === this.currentTheme) {
        button.classList.add('active');
      } else {
        button.classList.remove('active');
      }
    });
  }

  /**
   * Setup event listeners
   */
  setupListeners() {
    // Theme button clicks
    document.addEventListener('click', (e) => {
      const button = e.target.closest('.theme-button');
      if (button) {
        const theme = button.getAttribute('data-theme');
        if (theme && Object.values(THEMES).includes(theme)) {
          this.applyTheme(theme);
        }
      }
    });

    // Listen for system theme changes
    if (window.matchMedia) {
      const lightModeQuery = window.matchMedia('(prefers-color-scheme: light)');
      const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');

      const handleSystemThemeChange = () => {
        // Only auto-switch if user hasn't manually selected a theme
        const hasManualSelection = localStorage.getItem(STORAGE_KEY);
        if (!hasManualSelection) {
          if (lightModeQuery.matches) {
            this.applyTheme(THEMES.LIGHT);
          } else if (darkModeQuery.matches) {
            this.applyTheme(THEMES.DARK);
          }
        }
      };

      // Modern browsers
      if (lightModeQuery.addEventListener) {
        lightModeQuery.addEventListener('change', handleSystemThemeChange);
        darkModeQuery.addEventListener('change', handleSystemThemeChange);
      }
      // Legacy browsers
      else if (lightModeQuery.addListener) {
        lightModeQuery.addListener(handleSystemThemeChange);
        darkModeQuery.addListener(handleSystemThemeChange);
      }
    }
  }

  /**
   * Get current theme
   */
  getCurrentTheme() {
    return this.currentTheme;
  }

  /**
   * Cycle to next theme (for keyboard shortcuts)
   */
  cycleTheme() {
    const themes = Object.values(THEMES);
    const currentIndex = themes.indexOf(this.currentTheme);
    const nextIndex = (currentIndex + 1) % themes.length;
    this.applyTheme(themes[nextIndex]);
  }
}

// Initialize theme switcher when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.themeSwitcher = new ThemeSwitcher();
  });
} else {
  window.themeSwitcher = new ThemeSwitcher();
}

// Optional: Add keyboard shortcut (Ctrl+Shift+T) to cycle themes
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.shiftKey && e.key === 'T') {
    e.preventDefault();
    if (window.themeSwitcher) {
      window.themeSwitcher.cycleTheme();
    }
  }
});

// Export for use in other modules if needed
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ThemeSwitcher, THEMES };
}
