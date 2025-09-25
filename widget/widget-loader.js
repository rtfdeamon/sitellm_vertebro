(() => {
  const CURRENT_VERSION = '1.0.0';

  const LOADER_KEY = '__sitellmWidgetStyles';

  function ensureStyles(accent) {
    if (document.getElementById(LOADER_KEY)) return;
    const style = document.createElement('style');
    style.id = LOADER_KEY;
    style.textContent = `
    @keyframes sitellm-pulse {
      0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(${accent}, 0.45); }
      70% { transform: scale(1.03); box-shadow: 0 0 0 12px rgba(${accent}, 0); }
      100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(${accent}, 0); }
    }
    @keyframes sitellm-slide-up {
      from { transform: translateY(16px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
    .sitellm-widget-launcher {
      position: fixed;
      right: 24px;
      bottom: 24px;
      z-index: 2147483646;
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-radius: 999px;
      font-family: "Inter", system-ui, -apple-system, Segoe UI, sans-serif;
      background: rgba(${accent}, 1);
      color: #fff;
      border: none;
      cursor: pointer;
      box-shadow: 0 18px 40px rgba(15, 23, 42, 0.35);
      animation: sitellm-pulse 3s ease-in-out infinite;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .sitellm-widget-launcher:hover {
      transform: translateY(-2px);
      box-shadow: 0 22px 60px rgba(15, 23, 42, 0.45);
    }
    .sitellm-widget-launcher .sitellm-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: rgba(255,255,255,0.18);
      display: grid;
      place-items: center;
      font-weight: 600;
      letter-spacing: 0.04em;
    }
    .sitellm-widget-launcher .sitellm-copy {
      display: flex;
      flex-direction: column;
      line-height: 1.1;
      text-align: left;
    }
    .sitellm-widget-launcher .sitellm-copy strong {
      font-size: 13px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .sitellm-widget-launcher .sitellm-copy span {
      font-size: 12px;
      opacity: 0.8;
    }
    .sitellm-widget-frame {
      position: fixed;
      right: 24px;
      bottom: 96px;
      width: min(420px, calc(100vw - 32px));
      max-height: min(680px, calc(100vh - 120px));
      background: #0f1117;
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 24px 68px rgba(15, 23, 42, 0.55);
      border: 1px solid rgba(148, 163, 184, 0.25);
      display: none;
      animation: sitellm-slide-up 0.24s ease forwards;
      z-index: 2147483647;
    }
    .sitellm-widget-frame.is-open { display: block; }
    .sitellm-widget-frame iframe {
      width: 100%;
      height: 100%;
      border: none;
    }
    .sitellm-widget-overlay {
      position: fixed;
      inset: 0;
      background: rgba(15, 19, 36, 0.55);
      backdrop-filter: blur(3px);
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s ease;
      z-index: 2147483645;
    }
    .sitellm-widget-overlay.is-open {
      opacity: 1;
      pointer-events: auto;
    }
    .sitellm-inline-card {
      font-family: "Inter", system-ui, -apple-system, Segoe UI, sans-serif;
      border-radius: 18px;
      border: 1px solid rgba(148, 163, 184, 0.25);
      box-shadow: 0 20px 48px rgba(15, 23, 42, 0.35);
      overflow: hidden;
      animation: sitellm-slide-up 0.28s ease;
    }
    .sitellm-inline-card iframe {
      width: 100%;
      height: 100%;
      border: none;
      display: block;
    }
    .sitellm-inline-header {
      padding: 16px 20px 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #0f172a;
    }
    .sitellm-inline-header strong {
      font-size: 15px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .sitellm-inline-header span {
      font-size: 13px;
      color: rgba(15, 23, 42, 0.75);
    }
    .sitellm-inline-body {
      padding: 12px 20px 20px;
    }
    .sitellm-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: rgba(${accent}, 0.18);
      color: rgba(${accent}, 1);
    }
    `;
    document.head.appendChild(style);
  }

  function hexToRgb(hex) {
    if (!hex) return '79, 124, 255';
    const normalized = hex.replace('#', '');
    let r = 79, g = 124, b = 255;
    if (normalized.length === 3) {
      r = parseInt(normalized[0] + normalized[0], 16);
      g = parseInt(normalized[1] + normalized[1], 16);
      b = parseInt(normalized[2] + normalized[2], 16);
    } else if (normalized.length === 6) {
      r = parseInt(normalized.slice(0, 2), 16);
      g = parseInt(normalized.slice(2, 4), 16);
      b = parseInt(normalized.slice(4, 6), 16);
    }
    return `${r}, ${g}, ${b}`;
  }

  function resolveBaseUrl(script) {
    const fromAttr = script.dataset.baseUrl;
    if (fromAttr) {
      return fromAttr.replace(/\/$/, '');
    }
    try {
      const url = new URL(script.src);
      url.pathname = url.pathname.split('/').slice(0, -1).join('/') || '/';
      return url.origin;
    } catch (err) {
      return window.location.origin;
    }
  }

  function sessionKey(project) {
    const storageKey = `sitellm-widget-session-${project || 'default'}`;
    try {
      const stored = window.localStorage.getItem(storageKey);
      if (stored) return stored;
      const generated = (crypto.randomUUID && crypto.randomUUID()) ||
        Math.random().toString(36).slice(2) + Date.now().toString(36);
      window.localStorage.setItem(storageKey, generated);
      return generated;
    } catch (err) {
      return Math.random().toString(36).slice(2);
    }
  }

  function openFloating(frame, overlay) {
    frame.classList.add('is-open');
    overlay.classList.add('is-open');
  }

  function closeFloating(frame, overlay) {
    frame.classList.remove('is-open');
    overlay.classList.remove('is-open');
  }

  function createFloatingEmbed(script, options) {
    const { frameSrc, accentRgb, launcherTitle, launcherSubtitle, launcherIcon } = options;
    ensureStyles(accentRgb);

    const overlay = document.createElement('div');
    overlay.className = 'sitellm-widget-overlay';

    const frame = document.createElement('div');
    frame.className = 'sitellm-widget-frame';
    frame.style.width = options.width;
    frame.style.height = options.height;

    const iframe = document.createElement('iframe');
    iframe.src = frameSrc;
    iframe.loading = 'lazy';
    iframe.referrerPolicy = 'no-referrer-when-downgrade';
    iframe.allow = 'microphone; clipboard-read; clipboard-write;';
    frame.appendChild(iframe);

    const launcher = document.createElement('button');
    launcher.type = 'button';
    launcher.className = 'sitellm-widget-launcher';
    launcher.innerHTML = `
      <span class="sitellm-avatar">${launcherIcon}</span>
      <span class="sitellm-copy">
        <strong>${launcherTitle}</strong>
        <span>${launcherSubtitle}</span>
      </span>
    `;

    launcher.addEventListener('click', () => {
      const isOpen = frame.classList.contains('is-open');
      if (isOpen) {
        closeFloating(frame, overlay);
      } else {
        openFloating(frame, overlay);
      }
    });
    overlay.addEventListener('click', () => closeFloating(frame, overlay));

    document.body.appendChild(overlay);
    document.body.appendChild(frame);
    document.body.appendChild(launcher);
  }

  function createInlineEmbed(script, options) {
    ensureStyles(options.accentRgb);
    const wrapper = document.createElement('div');
    wrapper.className = 'sitellm-inline-card';
    wrapper.style.width = options.width;
    wrapper.style.maxWidth = '100%';
    wrapper.style.height = options.height;

    const iframe = document.createElement('iframe');
    iframe.src = options.frameSrc;
    iframe.loading = 'lazy';
    iframe.allow = 'microphone; clipboard-read; clipboard-write;';
    wrapper.appendChild(iframe);

    script.insertAdjacentElement('beforebegin', wrapper);
  }

  function buildFrameSrc(base, project, session, extraParams) {
    const search = new URLSearchParams({ embed: '1', session: session });
    if (project) search.set('project', project);
    if (extraParams.theme) search.set('theme', extraParams.theme);
    if (extraParams.debug === '1') search.set('debug', '1');
    return `${base}/widget/index.html?${search.toString()}`;
  }

  function init(script) {
    const base = resolveBaseUrl(script);
    const accentRgb = hexToRgb(script.dataset.color || '#4f7cff');
    const project = script.dataset.project || '';
    const variant = (script.dataset.variant || 'floating').toLowerCase();
    const width = script.dataset.width || (variant === 'inline' ? '100%' : '380px');
    const height = script.dataset.height || (variant === 'inline' ? '480px' : '640px');
    const launcherTitle = script.dataset.title || 'AI Consultant';
    const launcherSubtitle = script.dataset.subtitle || 'Ask me anything';
    const launcherIcon = script.dataset.icon || 'AI';
    const theme = script.dataset.theme || '';
    const debug = script.dataset.debug || '';

    const session = sessionKey(project);
    const frameSrc = buildFrameSrc(base, project, session, { theme, debug });

    const options = {
      frameSrc,
      accentRgb,
      width,
      height,
      launcherTitle,
      launcherSubtitle,
      launcherIcon,
    };

    if (variant === 'inline') {
      createInlineEmbed(script, options);
    } else {
      createFloatingEmbed(script, options);
    }
  }

  function bootstrap() {
    const script = document.currentScript;
    if (!script) return;
    try {
      init(script);
    } catch (err) {
      console.error('[SiteLLM widget-loader]', err);
    }
  }

  bootstrap();

  window.SiteLLMWidgetLoader = {
    version: CURRENT_VERSION,
  };
})();
