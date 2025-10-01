(() => {
  const CURRENT_VERSION = '1.0.0';
  const STYLE_ID = '__sitellmVoiceAvatarStyles';
  const projectConfigCache = new Map();

  const globalRoot = window.SiteLLMVoiceAvatar || {};
  const instanceRegistry = globalRoot.instances || [];
  let bookOverlaySequence = 0;

  const ORIENTATION_DEFAULT = 'bottom-right';
  const ORIENTATION_ALIAS_MAP = new Map([
    ['bottom-right', 'bottom-right'],
    ['bottomright', 'bottom-right'],
    ['right-bottom', 'bottom-right'],
    ['br', 'bottom-right'],
    ['bottom-left', 'bottom-left'],
    ['bottomleft', 'bottom-left'],
    ['left-bottom', 'bottom-left'],
    ['bl', 'bottom-left'],
    ['top-right', 'top-right'],
    ['topright', 'top-right'],
    ['right-top', 'top-right'],
    ['tr', 'top-right'],
    ['top-left', 'top-left'],
    ['topleft', 'top-left'],
    ['left-top', 'top-left'],
    ['tl', 'top-left'],
  ]);
  const ORIENTATION_CLASS_MAP = {
    'bottom-right': 'sitellm-anchor-bottom-right',
    'bottom-left': 'sitellm-anchor-bottom-left',
    'top-right': 'sitellm-anchor-top-right',
    'top-left': 'sitellm-anchor-top-left',
  };
  const ORIENTATION_CLASSES = Object.values(ORIENTATION_CLASS_MAP);

  function registerInstance(instance) {
    instanceRegistry.push(instance);
    try {
      document.dispatchEvent(new CustomEvent('sitellm-voice-avatar-ready', {
        detail: instance,
      }));
    } catch (_) {
      // ignore subscriber errors
    }
  }

  function unregisterInstance(instance) {
    const idx = instanceRegistry.indexOf(instance);
    if (idx >= 0) {
      instanceRegistry.splice(idx, 1);
    }
    try {
      document.dispatchEvent(new CustomEvent('sitellm-voice-avatar-destroyed', {
        detail: instance,
      }));
    } catch (_) {
      // ignore subscriber errors
    }
  }

  function normalizeOrientation(value) {
    if (!value || typeof value !== 'string') {
      return ORIENTATION_DEFAULT;
    }
    const normalized = value.trim().toLowerCase().replace(/_/g, '-').replace(/\s+/g, '-');
    return ORIENTATION_ALIAS_MAP.get(normalized) || ORIENTATION_DEFAULT;
  }

  function applyOrientationClass(wrapper, orientation) {
    if (!wrapper) return;
    for (const className of ORIENTATION_CLASSES) {
      wrapper.classList.remove(className);
    }
    const resolved = ORIENTATION_CLASS_MAP[orientation] || ORIENTATION_CLASS_MAP[ORIENTATION_DEFAULT];
    if (resolved) {
      wrapper.classList.add(resolved);
    }
  }

  const CHARACTER_PRESETS = {
    nova: {
      label: 'Nova',
      description: 'Empathic product specialist',
      svg: `<?xml version="1.0" encoding="UTF-8"?>
        <svg viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Nova animated avatar">
          <defs>
            <radialGradient id="nova_bg" cx="48%" cy="36%" r="62%">
              <stop offset="0%" stop-color="#f7f2ff" stop-opacity="0.95" />
              <stop offset="100%" stop-color="#c7bcff" stop-opacity="0.18" />
            </radialGradient>
            <linearGradient id="nova_skin" x1="50%" y1="18%" x2="52%" y2="94%">
              <stop offset="0%" stop-color="#ffe6d8" />
              <stop offset="55%" stop-color="#f8c3a8" />
              <stop offset="100%" stop-color="#e9a489" />
            </linearGradient>
            <linearGradient id="nova_hair" x1="18%" y1="0%" x2="88%" y2="100%">
              <stop offset="0%" stop-color="#372760" />
              <stop offset="100%" stop-color="#1f163c" />
            </linearGradient>
            <linearGradient id="nova_lips" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#d8657d" />
              <stop offset="100%" stop-color="#b24b61" />
            </linearGradient>
          </defs>
          <circle cx="80" cy="80" r="74" fill="url(#nova_bg)" />
          <path d="M28 94c4-34 22-56 52-58 26-2 44 12 54 36 4 10 6 22 3 32-6 26-26 42-57 42s-51-16-57-42c-2-8-1-18 5-28z" fill="url(#nova_hair)" />
          <circle cx="80" cy="94" r="44" fill="url(#nova_skin)" />
          <path d="M44 96c12-8 24-12 36-12s24 4 36 12c-6 22-18 32-36 32s-30-10-36-32z" fill="#f0bfa5" opacity="0.65" />
          <path d="M46 80c10-12 30-16 48-12 12 2 20 6 28 12-8-26-26-38-44-38-20 0-36 12-44 38z" fill="#2d2150" />
          <path class="avatar-eye" d="M56 98c6-4 16-4 22 0 3 2 0 6-3 6H59c-4 0-7-4-3-6z" fill="#fff" />
          <circle class="avatar-eye" cx="68" cy="101" r="4.5" fill="#231b39" />
          <path class="avatar-eye" d="M104 98c-6-4-16-4-22 0-3 2 0 6 3 6h16c4 0 7-4 3-6z" fill="#fff" />
          <circle class="avatar-eye" cx="92" cy="101" r="4.5" fill="#231b39" />
          <circle cx="60" cy="110" r="3.4" fill="#f7b7a4" opacity="0.85" />
          <circle cx="100" cy="110" r="3.4" fill="#f7b7a4" opacity="0.85" />
          <path d="M58 92c8-6 18-6 26 0" stroke="#2f1f45" stroke-width="2.4" stroke-linecap="round" opacity="0.5" />
          <path class="avatar-mouth" d="M64 126c8 8 24 8 32 0 1-3-1-5-4-5H68c-3 0-5 2-4 5z" fill="url(#nova_lips)" />
          <path d="M68 128c6 4 18 4 24 0-4 4-12 8-12 8s-8-4-12-8z" fill="#f7c8b6" />
        </svg>`
    },
    atlas: {
      label: 'Atlas',
      description: 'Calm operations engineer',
      svg: `<?xml version="1.0" encoding="UTF-8"?>
        <svg viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Atlas animated avatar">
          <defs>
            <radialGradient id="atlas_bg" cx="46%" cy="32%" r="64%">
              <stop offset="0%" stop-color="#f2f8ff" stop-opacity="0.9" />
              <stop offset="100%" stop-color="#c8dafe" stop-opacity="0.2" />
            </radialGradient>
            <linearGradient id="atlas_skin" x1="50%" y1="20%" x2="52%" y2="96%">
              <stop offset="0%" stop-color="#f5d6b4" />
              <stop offset="55%" stop-color="#dfb18a" />
              <stop offset="100%" stop-color="#c79a72" />
            </linearGradient>
            <linearGradient id="atlas_hair" x1="20%" y1="10%" x2="80%" y2="95%">
              <stop offset="0%" stop-color="#2d2a38" />
              <stop offset="100%" stop-color="#141722" />
            </linearGradient>
            <linearGradient id="atlas_beard" x1="30%" y1="30%" x2="80%" y2="90%">
              <stop offset="0%" stop-color="#1d1f2c" />
              <stop offset="100%" stop-color="#12131d" />
            </linearGradient>
            <linearGradient id="atlas_mouth" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#9f5240" />
              <stop offset="100%" stop-color="#783425" />
            </linearGradient>
          </defs>
          <circle cx="80" cy="80" r="74" fill="url(#atlas_bg)" />
          <path d="M26 94c6-34 24-54 50-58 24-3 42 9 52 30 6 12 8 24 5 36-6 26-25 42-57 42s-51-16-57-42c-3-10-2-22 7-32z" fill="url(#atlas_hair)" />
          <circle cx="80" cy="96" r="44" fill="url(#atlas_skin)" />
          <path d="M50 90c12-10 22-14 30-14s16 4 30 14c-6 22-16 32-30 32s-24-10-30-32z" fill="url(#atlas_beard)" opacity="0.9" />
          <path d="M48 76c8-16 32-20 52-12 8 3 14 6 20 12-6-24-20-36-40-36-20 0-34 10-40 36z" fill="#1a1b26" />
          <path class="avatar-eye" d="M58 100c6-4 14-4 19 0 3 2 0 6-3 6H61c-4 0-7-4-3-6z" fill="#fff" />
          <circle class="avatar-eye" cx="68" cy="103" r="4" fill="#131720" />
          <path class="avatar-eye" d="M102 100c-6-4-14-4-19 0-3 2 0 6 3 6h13c4 0 7-4 3-6z" fill="#fff" />
          <circle class="avatar-eye" cx="92" cy="103" r="4" fill="#131720" />
          <path d="M58 92c6-6 14-6 20 0" stroke="#1e202a" stroke-width="2.6" stroke-linecap="round" opacity="0.5" />
          <path class="avatar-mouth" d="M64 126c7 6 22 6 30 0 1-3-1-5-4-5H68c-3 0-5 2-4 5z" fill="url(#atlas_mouth)" />
          <path d="M62 130c8 6 24 6 34 0-6 6-14 10-17 10s-11-4-17-10z" fill="#d3ad8a" opacity="0.6" />
        </svg>`
    },
    cosmo: {
      label: 'Cosmo',
      description: 'Futuristic guide',
      svg: `<?xml version="1.0" encoding="UTF-8"?>
        <svg viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Cosmo animated avatar">
          <defs>
            <radialGradient id="cosmo_bg" cx="50%" cy="34%" r="64%">
              <stop offset="0%" stop-color="#e5f7ff" stop-opacity="0.95" />
              <stop offset="100%" stop-color="#9ed5ff" stop-opacity="0.18" />
            </radialGradient>
            <linearGradient id="cosmo_skin" x1="48%" y1="18%" x2="52%" y2="88%">
              <stop offset="0%" stop-color="#fbe1cf" />
              <stop offset="60%" stop-color="#efbea0" />
              <stop offset="100%" stop-color="#db9a7a" />
            </linearGradient>
            <linearGradient id="cosmo_hair" x1="20%" y1="0%" x2="80%" y2="100%">
              <stop offset="0%" stop-color="#14263f" />
              <stop offset="100%" stop-color="#0c1624" />
            </linearGradient>
            <linearGradient id="cosmo_lips" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#ff7a8d" />
              <stop offset="100%" stop-color="#c6546d" />
            </linearGradient>
          </defs>
          <circle cx="80" cy="80" r="74" fill="url(#cosmo_bg)" />
          <path d="M32 92c6-30 24-52 54-54 24-2 40 12 48 34 4 10 6 22 2 32-8 26-26 40-54 40s-46-14-54-40c-2-8-1-18 4-28z" fill="url(#cosmo_hair)" />
          <circle cx="80" cy="94" r="42" fill="url(#cosmo_skin)" />
          <path d="M48 94c12-10 20-12 32-12s20 2 32 12c-4 20-18 28-32 28s-28-8-32-28z" fill="#f0c0a3" opacity="0.7" />
          <path d="M50 78c8-18 30-22 48-16 10 4 16 8 22 14-10-26-24-34-40-34-18 0-34 10-40 36z" fill="#132841" />
          <path class="avatar-eye" d="M56 98c6-4 14-4 20 0 3 2 0 6-3 6H59c-4 0-7-4-3-6z" fill="#fff" />
          <circle class="avatar-eye" cx="66" cy="101" r="4.2" fill="#101b2a" />
          <path class="avatar-eye" d="M104 98c-6-4-14-4-20 0-3 2 0 6 3 6h14c4 0 7-4 3-6z" fill="#fff" />
          <circle class="avatar-eye" cx="94" cy="101" r="4.2" fill="#101b2a" />
          <path d="M58 90c6-6 16-6 24 0" stroke="#1b2a3f" stroke-width="2.2" stroke-linecap="round" opacity="0.55" />
          <path class="avatar-mouth" d="M64 124c7 8 24 8 31 0 1-3-1-5-4-5H68c-3 0-5 2-4 5z" fill="url(#cosmo_lips)" />
          <path d="M68 126c6 4 18 4 24 0-4 6-10 8-12 8s-8-2-12-8z" fill="#f6c7b3" />
        </svg>`
    },
    luna: {
      label: 'Luna',
      description: 'Warm customer success partner',
      svg: `<?xml version="1.0" encoding="UTF-8"?>
        <svg viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Luna animated avatar">
          <defs>
            <radialGradient id="luna_bg" cx="46%" cy="32%" r="62%">
              <stop offset="0%" stop-color="#fff0f1" stop-opacity="0.94" />
              <stop offset="100%" stop-color="#f6ccd6" stop-opacity="0.2" />
            </radialGradient>
            <linearGradient id="luna_skin" x1="50%" y1="18%" x2="52%" y2="95%">
              <stop offset="0%" stop-color="#ffe1d4" />
              <stop offset="60%" stop-color="#f6bfa3" />
              <stop offset="100%" stop-color="#e69f85" />
            </linearGradient>
            <linearGradient id="luna_hair" x1="16%" y1="6%" x2="84%" y2="94%">
              <stop offset="0%" stop-color="#2a1818" />
              <stop offset="100%" stop-color="#4f2b26" />
            </linearGradient>
            <linearGradient id="luna_lips" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#d75d6e" />
              <stop offset="100%" stop-color="#ad3f52" />
            </linearGradient>
          </defs>
          <circle cx="80" cy="80" r="74" fill="url(#luna_bg)" />
          <path d="M30 94c4-30 20-52 46-56 24-4 42 8 52 30 6 12 6 26 2 36-8 26-26 40-54 40s-46-14-54-40c-2-8-2-18 8-28z" fill="url(#luna_hair)" />
          <circle cx="80" cy="94" r="42" fill="url(#luna_skin)" />
          <path d="M50 94c12-8 20-10 30-10s18 2 30 10c-6 20-18 28-30 28s-24-8-30-28z" fill="#f3c0a8" opacity="0.7" />
          <path d="M50 78c10-18 30-22 46-16 12 4 18 8 26 16-10-28-26-38-44-38-16 0-32 10-40 38z" fill="#3b2421" />
          <path class="avatar-eye" d="M58 100c6-4 12-4 18 0 3 2 0 6-3 6H60c-4 0-6-4-2-6z" fill="#fff" />
          <circle class="avatar-eye" cx="66" cy="103" r="4" fill="#221411" />
          <path class="avatar-eye" d="M104 100c-6-4-12-4-18 0-3 2 0 6 3 6h12c4 0 6-4 3-6z" fill="#fff" />
          <circle class="avatar-eye" cx="96" cy="103" r="4" fill="#221411" />
          <circle cx="60" cy="110" r="3.2" fill="#f7b5a2" opacity="0.9" />
          <circle cx="100" cy="110" r="3.2" fill="#f7b5a2" opacity="0.9" />
          <path d="M58 92c6-6 14-6 22 0" stroke="#42211d" stroke-width="2.2" stroke-linecap="round" opacity="0.5" />
          <path class="avatar-mouth" d="M64 124c7 8 22 8 30 0 1-3-1-5-4-5H68c-3 0-5 2-4 5z" fill="url(#luna_lips)" />
          <path d="M68 126c6 4 16 4 22 0-4 6-10 8-11 8s-7-2-11-8z" fill="#f6c4b3" />
        </svg>`
    },
    amir: {
      label: 'Amir',
      description: 'Thoughtful technical guide',
      svg: `<?xml version="1.0" encoding="UTF-8"?>
        <svg viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Amir animated avatar">
          <defs>
            <radialGradient id="amir_bg" cx="48%" cy="30%" r="64%">
              <stop offset="0%" stop-color="#ecf5ff" stop-opacity="0.94" />
              <stop offset="100%" stop-color="#c8ddff" stop-opacity="0.18" />
            </radialGradient>
            <linearGradient id="amir_skin" x1="50%" y1="18%" x2="52%" y2="96%">
              <stop offset="0%" stop-color="#ffd9b8" />
              <stop offset="58%" stop-color="#f2b687" />
              <stop offset="100%" stop-color="#d99a6b" />
            </linearGradient>
            <linearGradient id="amir_hair" x1="16%" y1="8%" x2="84%" y2="94%">
              <stop offset="0%" stop-color="#1a2232" />
              <stop offset="100%" stop-color="#101823" />
            </linearGradient>
            <linearGradient id="amir_beard" x1="20%" y1="40%" x2="80%" y2="90%">
              <stop offset="0%" stop-color="#182332" />
              <stop offset="100%" stop-color="#101822" />
            </linearGradient>
            <linearGradient id="amir_lips" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#a24f3e" />
              <stop offset="100%" stop-color="#7b3726" />
            </linearGradient>
          </defs>
          <circle cx="80" cy="80" r="74" fill="url(#amir_bg)" />
          <path d="M32 96c4-30 18-50 44-56 26-6 46 6 56 30 6 12 6 24 2 34-8 28-28 44-58 44s-50-16-58-44c-2-8-2-18 6-28z" fill="url(#amir_hair)" />
          <circle cx="80" cy="98" r="42" fill="url(#amir_skin)" />
          <path d="M50 100c12-10 20-12 30-12s18 2 30 12c-6 22-18 30-30 30s-24-8-30-30z" fill="url(#amir_beard)" opacity="0.92" />
          <path d="M50 82c8-20 30-24 46-16 10 4 16 8 22 16-8-26-22-38-40-38-16 0-30 10-38 38z" fill="#111b27" />
          <path class="avatar-eye" d="M58 102c5-4 12-4 17 0 3 2 0 6-3 6H60c-4 0-6-4-2-6z" fill="#fff" />
          <circle class="avatar-eye" cx="66" cy="105" r="3.8" fill="#141820" />
          <path class="avatar-eye" d="M104 102c-5-4-12-4-17 0-3 2 0 6 3 6h11c4 0 6-4 3-6z" fill="#fff" />
          <circle class="avatar-eye" cx="96" cy="105" r="3.8" fill="#141820" />
          <path d="M60 94c6-6 14-6 20 0" stroke="#222b3a" stroke-width="2.4" stroke-linecap="round" opacity="0.55" />
          <path class="avatar-mouth" d="M64 124c7 6 22 6 30 0 1-3-1-5-4-5H68c-3 0-5 2-4 5z" fill="url(#amir_lips)" />
          <path d="M64 128c8 6 22 6 30 0-6 6-12 10-15 10s-9-4-15-10z" fill="#e5b18a" />
        </svg>`
    },
    sofia: {
      label: 'Sofia',
      description: 'Confident sales lead',
      svg: `<?xml version="1.0" encoding="UTF-8"?>
        <svg viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Sofia animated avatar">
          <defs>
            <radialGradient id="sofia_bg" cx="48%" cy="30%" r="64%">
              <stop offset="0%" stop-color="#f6f4ff" stop-opacity="0.94" />
              <stop offset="100%" stop-color="#d6d7ff" stop-opacity="0.2" />
            </radialGradient>
            <linearGradient id="sofia_skin" x1="50%" y1="18%" x2="52%" y2="94%">
              <stop offset="0%" stop-color="#fddbcc" />
              <stop offset="58%" stop-color="#f0b7a0" />
              <stop offset="100%" stop-color="#d79a82" />
            </linearGradient>
            <linearGradient id="sofia_hair" x1="18%" y1="10%" x2="82%" y2="96%">
              <stop offset="0%" stop-color="#311927" />
              <stop offset="100%" stop-color="#512d43" />
            </linearGradient>
            <linearGradient id="sofia_lips" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#b34960" />
              <stop offset="100%" stop-color="#8f3047" />
            </linearGradient>
          </defs>
          <circle cx="80" cy="80" r="74" fill="url(#sofia_bg)" />
          <path d="M30 92c0-28 16-52 42-60 26-8 46-2 60 20 6 10 8 22 6 34-6 30-26 46-55 46s-49-16-55-46c-2-8-2-16 2-24z" fill="url(#sofia_hair)" />
          <circle cx="80" cy="94" r="40" fill="url(#sofia_skin)" />
          <path d="M50 96c10-10 20-12 30-12s20 2 30 12c-6 22-18 30-30 30s-24-8-30-30z" fill="#edb69e" opacity="0.7" />
          <path d="M50 80c10-18 28-24 44-18 12 4 18 8 26 16-10-28-24-38-40-38-16 0-32 10-40 40z" fill="#3f2434" />
          <path class="avatar-eye" d="M58 100c5-4 12-4 18 0 3 2 0 6-3 6H60c-4 0-6-4-2-6z" fill="#fff" />
          <circle class="avatar-eye" cx="66" cy="103" r="3.8" fill="#22101d" />
          <path class="avatar-eye" d="M102 100c-5-4-12-4-18 0-3 2 0 6 3 6h12c4 0 6-4 3-6z" fill="#fff" />
          <circle class="avatar-eye" cx="94" cy="103" r="3.8" fill="#22101d" />
          <circle cx="60" cy="110" r="3.2" fill="#f5b2a0" opacity="0.85" />
          <circle cx="98" cy="110" r="3.2" fill="#f5b2a0" opacity="0.85" />
          <path d="M58 92c6-6 14-6 20 0" stroke="#3a1f2d" stroke-width="2.2" stroke-linecap="round" opacity="0.5" />
          <path class="avatar-mouth" d="M64 124c7 6 22 6 30 0 1-3-1-5-4-5H68c-3 0-5 2-4 5z" fill="url(#sofia_lips)" />
          <path d="M66 128c6 4 18 4 24 0-4 6-10 8-12 8s-8-2-12-8z" fill="#f5c4b4" />
        </svg>`
    },
  };

  const MODE_TEXT = 'text';
  const MODE_VOICE = 'voice';
  const MODE_AVATAR = 'avatar';

  const assistantUtteranceHistory = [];
  const INTERRUPT_KEYWORDS = [
    'стоп',
    'остановись',
    'останови',
    'прекрати',
    'хватит',
    'прекращай',
    'пауза',
    'stop',
    'pause',
    'cancel',
    'silence',
  ];

  function normalizeUtterance(text) {
    if (!text) return '';
    return stripEmojis(text)
      .toLowerCase()
      .replace(/["'`]+/g, '')
      .replace(/[.,!?;:()\[\]{}«»…]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function tokenSet(value) {
    return new Set(normalizeUtterance(value).split(' ').filter(Boolean));
  }

  const INTERRUPT_TOKEN_SET = new Set(INTERRUPT_KEYWORDS);

  function containsInterruptCommand(text) {
    const tokens = tokenSet(text);
    if (!tokens || tokens.size === 0) return false;
    for (const token of tokens) {
      if (INTERRUPT_TOKEN_SET.has(token)) {
        return true;
      }
    }
    return false;
  }

  function similarityScore(a, b) {
    if (!a || !b) return 0;
    if (a === b) return 1;
    if (a.includes(b) || b.includes(a)) {
      const minLen = Math.min(a.length, b.length);
      const maxLen = Math.max(a.length, b.length);
      return minLen / maxLen;
    }
    const tokensA = tokenSet(a);
    const tokensB = tokenSet(b);
    if (!tokensA.size || !tokensB.size) return 0;
    let intersection = 0;
    tokensA.forEach((token) => {
      if (tokensB.has(token)) intersection += 1;
    });
    const union = tokensA.size + tokensB.size - intersection;
    return union === 0 ? 0 : intersection / union;
  }

  function rememberAssistantUtterance(text) {
    const normalized = normalizeUtterance(text);
    if (!normalized || normalized.length < 6) return;
    assistantUtteranceHistory.push({ raw: text, normalized, ts: Date.now() });
    if (assistantUtteranceHistory.length > 6) {
      assistantUtteranceHistory.shift();
    }
  }

  function isEchoOfAssistant(text) {
    const normalized = normalizeUtterance(text);
    if (!normalized || normalized.length < 6) return false;
    const now = Date.now();
    return assistantUtteranceHistory.some((entry) => {
      if (!entry) return false;
      if (now - entry.ts > 120000) return false;
      const score = similarityScore(normalized, entry.normalized);
      return score >= 0.65;
    });
  }

  function ensureStyles(accent) {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
    @keyframes sitellmAvatarFloat {
      0% { transform: translateY(0px) scale(1); box-shadow: 0 12px 24px rgba(${accent}, 0.25); }
      50% { transform: translateY(-6px) scale(1.01); box-shadow: 0 22px 32px rgba(${accent}, 0.18); }
      100% { transform: translateY(0px) scale(1); box-shadow: 0 12px 24px rgba(${accent}, 0.25); }
    }
    @keyframes sitellmMouthTalk {
      0%, 100% { transform: scaleY(0.35); }
      50% { transform: scaleY(1); }
    }
    @keyframes sitellmBlink {
      0%, 88%, 100% { transform: scaleY(1); }
      90%, 92% { transform: scaleY(0.1); }
    }
    .sitellm-voice-wrapper {
      position: fixed;
      z-index: 2147483601;
      max-width: min(420px, calc(100vw - 32px));
      width: min(360px, calc(100vw - 32px));
      box-sizing: border-box;
    }
    .sitellm-voice-wrapper .sitellm-voice-widget {
      margin: 0;
      width: 100%;
    }
    .sitellm-voice-wrapper.sitellm-anchor-bottom-right { right: 24px; bottom: 24px; }
    .sitellm-voice-wrapper.sitellm-anchor-bottom-left { left: 24px; bottom: 24px; }
    .sitellm-voice-wrapper.sitellm-anchor-top-right { right: 24px; top: 24px; }
    .sitellm-voice-wrapper.sitellm-anchor-top-left { left: 24px; top: 24px; }
    @media (max-width: 640px) {
      .sitellm-voice-wrapper {
        width: calc(100vw - 24px);
        max-width: calc(100vw - 24px);
      }
      .sitellm-voice-wrapper.sitellm-anchor-bottom-right,
      .sitellm-voice-wrapper.sitellm-anchor-top-right {
        right: 12px;
      }
      .sitellm-voice-wrapper.sitellm-anchor-bottom-left,
      .sitellm-voice-wrapper.sitellm-anchor-top-left {
        left: 12px;
      }
      .sitellm-voice-wrapper.sitellm-anchor-bottom-right,
      .sitellm-voice-wrapper.sitellm-anchor-bottom-left {
        bottom: 12px;
      }
      .sitellm-voice-wrapper.sitellm-anchor-top-right,
      .sitellm-voice-wrapper.sitellm-anchor-top-left {
        top: 12px;
      }
    }
    .sitellm-voice-widget {
      position: relative;
      width: min(360px, 100%);
      max-height: 520px;
      overflow: hidden;
      margin: 24px auto;
      font-family: "Inter", system-ui, -apple-system, Segoe UI, sans-serif;
      border-radius: 24px;
      padding: 24px;
      color: #0f172a;
      background: linear-gradient(140deg, rgba(${accent}, 0.08), rgba(${accent}, 0.02));
      border: 1px solid rgba(${accent}, 0.25);
      box-shadow: 0 24px 64px rgba(15, 23, 42, 0.25);
      overflow: hidden;
    }
    .sitellm-voice-widget.mode-text .sitellm-voice-visual,
    .sitellm-voice-widget.mode-text .sitellm-voice-mic {
      display: none !important;
    }
    .sitellm-voice-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 18px;
    }
    .sitellm-voice-header strong {
      font-size: 15px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: rgba(${accent}, 1);
    }
    .sitellm-voice-avatar {
      position: relative;
      width: 118px;
      height: 118px;
      border-radius: 50%;
      background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.78), rgba(${accent}, 0.92));
      display: grid;
      place-items: center;
      font-weight: 700;
      color: #fff;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      animation: sitellmAvatarFloat 4.5s ease-in-out infinite;
      overflow: visible;
    }
    .sitellm-voice-avatar.has-character {
      background: radial-gradient(circle at 28% 30%, rgba(255,255,255,0.95), rgba(${accent}, 0.42));
      color: rgba(15, 23, 42, 0.8);
      letter-spacing: 0;
      box-shadow: 0 18px 40px rgba(${accent}, 0.32);
    }
    .sitellm-voice-avatar-label {
      position: relative;
      z-index: 3;
      font-size: 18px;
    }
    .sitellm-voice-avatar.has-character .sitellm-voice-avatar-label {
      display: none;
    }
    .sitellm-voice-avatar .sitellm-character-wrapper {
      position: absolute;
      inset: 6px;
      border-radius: 50%;
      overflow: hidden;
      background: radial-gradient(circle at 50% 20%, rgba(255,255,255,0.92), rgba(${accent}, 0.15));
      box-shadow: inset 0 0 0 1px rgba(${accent}, 0.25);
      z-index: 2;
    }
    .sitellm-voice-avatar .sitellm-character-wrapper svg,
    .sitellm-voice-avatar .sitellm-character-wrapper img {
      width: 100%;
      height: 100%;
      display: block;
      pointer-events: none;
    }
    .sitellm-voice-avatar .sitellm-character-wrapper .avatar-mouth,
    .sitellm-voice-avatar .sitellm-character-wrapper .avatar-eye {
      transform-box: fill-box;
      transform-origin: center;
    }
    .sitellm-voice-avatar.has-character .avatar-eye {
      animation: sitellmBlink 6.2s ease-in-out infinite;
    }
    .sitellm-voice-avatar.talking .avatar-eye {
      animation-duration: 4.2s;
    }
    .sitellm-voice-avatar.talking .avatar-mouth {
      animation: sitellmMouthTalk 0.38s ease-in-out infinite;
    }
    .sitellm-character-badge {
      position: absolute;
      bottom: -14px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(${accent}, 0.18);
      color: rgba(15, 23, 42, 0.8);
      font-size: 11px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 999px;
      letter-spacing: 0.06em;
      backdrop-filter: blur(6px);
      box-shadow: 0 4px 12px rgba(${accent}, 0.25);
    }
    .sitellm-voice-avatar .sitellm-character-wrapper img {
      object-fit: cover;
      pointer-events: none;
    }
    .sitellm-voice-visual {
      position: absolute;
      inset: -6px;
      border-radius: 50%;
      border: 2px solid rgba(${accent}, 0.32);
      pointer-events: none;
      opacity: 0;
      transform: scale(1);
      transition: opacity 0.2s ease, transform 0.15s ease;
      z-index: 1;
    }
    .sitellm-voice-visual.mic.active {
      opacity: 0.85;
      border-color: rgba(${accent}, 0.55);
      box-shadow: 0 0 0 6px rgba(${accent}, 0.12);
    }
    .sitellm-voice-visual.voice {
      border-color: rgba(255,255,255,0.55);
      box-shadow: 0 0 0 10px rgba(${accent}, 0.08);
    }
    .sitellm-voice-visual.voice.active {
      opacity: 0.9;
    }
    .sitellm-voice-content {
      display: flex;
      flex-direction: column;
      gap: 18px;
      max-height: 360px;
      overflow-y: auto;
      padding-right: 6px;
    }
    .sitellm-voice-status {
      font-size: 13px;
      line-height: 1.5;
      color: rgba(15, 23, 42, 0.68);
      min-height: 40px;
    }
    .sitellm-voice-status .user,
    .sitellm-voice-status .bot {
      display: block;
      margin-bottom: 6px;
      padding-left: 6px;
    }
    .sitellm-voice-status .bot {
      color: rgba(${accent}, 1);
    }
    .sitellm-voice-actions {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-top: 18px;
    }
    .sitellm-voice-mic {
      flex: none;
      width: 52px;
      height: 52px;
      border-radius: 50%;
      border: none;
      background: rgba(${accent}, 1);
      color: #fff;
      display: grid;
      place-items: center;
      cursor: pointer;
      font-size: 20px;
      box-shadow: 0 16px 40px rgba(${accent}, 0.35);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .sitellm-voice-mic.active {
      background: #fff;
      color: rgba(${accent}, 1);
      box-shadow: 0 20px 48px rgba(${accent}, 0.45);
      transform: scale(1.04);
    }
    .sitellm-voice-mic:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .sitellm-voice-transcript {
      flex: 1 1 auto;
      min-height: 48px;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(255,255,255,0.85);
      border: 1px solid rgba(${accent}, 0.18);
      font-size: 14px;
      line-height: 1.4;
      color: #0f172a;
      overflow-y: auto;
      max-height: 120px;
    }
    .sitellm-voice-error {
      margin-top: 12px;
      padding: 10px 12px;
      border-radius: 12px;
      background: rgba(239, 68, 68, 0.08);
      color: #b91c1c;
      font-size: 13px;
      display: none;
    }
    .sitellm-voice-error.show { display: block; }
    .sitellm-voice-input {
      display: none;
      width: 100%;
      margin-top: 12px;
    }
    .sitellm-voice-input textarea {
      width: 100%;
      min-height: 64px;
      border-radius: 14px;
      border: 1px solid rgba(${accent}, 0.24);
      padding: 12px;
      font-family: inherit;
      font-size: 14px;
      resize: vertical;
    }
    .sitellm-voice-input button {
      margin-top: 8px;
      padding: 8px 12px;
      border-radius: 10px;
      border: 1px solid rgba(${accent}, 0.3);
      background: rgba(${accent}, 0.12);
      color: rgba(${accent}, 1);
      cursor: pointer;
    }
    .sitellm-reading-panel {
      margin-top: 20px;
      padding: 16px;
      border-radius: 20px;
      background: linear-gradient(145deg, rgba(255, 252, 246, 0.96), rgba(248, 244, 232, 0.92));
      border: 1px solid rgba(${accent}, 0.22);
      box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.65);
      display: flex;
      flex-direction: column;
      gap: 14px;
      max-height: min(360px, 48vh);
      transition: transform 150ms ease, box-shadow 150ms ease;
    }
    .sitellm-reading-panel:hover {
      box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12), inset 0 0 0 1px rgba(255, 255, 255, 0.75);
      transform: translateY(-2px);
    }
    .sitellm-reading-panel.hidden {
      display: none;
    }
    .sitellm-reading-heading {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: rgba(${accent}, 0.88);
      gap: 8px;
    }
    .sitellm-reading-heading .label {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .sitellm-reading-heading .label::before {
      content: '📖';
      font-size: 14px;
    }
    .sitellm-reading-expand {
      padding: 6px 12px;
      border-radius: 12px;
      border: 1px solid rgba(${accent}, 0.3);
      background: rgba(${accent}, 0.12);
      color: rgba(${accent}, 0.96);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease;
    }
    .sitellm-reading-expand:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 8px 18px rgba(${accent}, 0.2);
    }
    .sitellm-reading-expand:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .sitellm-reading-source {
      font-size: 12px;
      color: rgba(15, 23, 42, 0.58);
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 6px;
      word-break: break-word;
    }
    .sitellm-reading-source::before {
      content: '🔗';
      font-size: 13px;
    }
    .sitellm-reading-source a {
      color: rgba(${accent}, 0.95);
      text-decoration: none;
    }
    .sitellm-reading-source a:hover {
      text-decoration: underline;
    }
    .sitellm-reading-placeholder {
      font-size: 13px;
      color: rgba(15, 23, 42, 0.55);
    }
    .sitellm-reading-scroll {
      overflow-y: auto;
      flex: 1 1 auto;
      padding-right: 6px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .sitellm-reading-scroll::-webkit-scrollbar {
      width: 6px;
    }
    .sitellm-reading-scroll::-webkit-scrollbar-thumb {
      background: rgba(${accent}, 0.35);
      border-radius: 8px;
    }
    .sitellm-reading-page {
      padding: 14px 16px;
      border-radius: 16px;
      border: 1px solid rgba(${accent}, 0.18);
      background: rgba(248, 250, 255, 0.9);
      box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
      cursor: pointer;
      transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
    }
    .sitellm-reading-page:hover {
      transform: translateY(-1px);
      box-shadow: 0 18px 32px rgba(15, 23, 42, 0.12);
    }
    .sitellm-reading-page.active {
      border-color: rgba(${accent}, 0.4);
      box-shadow: 0 22px 38px rgba(${accent}, 0.18);
    }
    .sitellm-reading-page h4 {
      margin: 0 0 6px;
      font-size: 15px;
      color: rgba(${accent}, 0.95);
    }
    .sitellm-reading-page-summary {
      font-size: 13px;
      color: rgba(15, 23, 42, 0.62);
      margin-bottom: 8px;
    }
    .sitellm-reading-segment p {
      margin: 6px 0;
      font-size: 13.5px;
      line-height: 1.58;
      color: rgba(15, 23, 42, 0.88);
    }
    .sitellm-reading-images {
      display: grid;
      gap: 8px;
      margin-top: 8px;
    }
    .sitellm-reading-images img {
      width: 100%;
      border-radius: 12px;
      object-fit: cover;
      max-height: 180px;
      border: 1px solid rgba(${accent}, 0.18);
    }
    .sitellm-reading-more {
      align-self: flex-end;
      padding: 6px 12px;
      border-radius: 10px;
      border: 1px solid rgba(${accent}, 0.3);
      background: rgba(${accent}, 0.12);
      color: rgba(${accent}, 1);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      cursor: pointer;
    }
    .sitellm-reading-more:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .sitellm-sources-panel {
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(248, 250, 255, 0.92);
      border: 1px solid rgba(${accent}, 0.2);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.55);
      display: none;
      flex-direction: column;
      gap: 6px;
    }
    .sitellm-sources-panel.show {
      display: flex;
    }
    .sitellm-sources-title {
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: rgba(${accent}, 0.82);
    }
    .sitellm-sources-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .sitellm-sources-list a {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: rgba(${accent}, 0.95);
      font-size: 13px;
      text-decoration: none;
      word-break: break-word;
    }
    .sitellm-sources-list a::before {
      content: '🔗';
      font-size: 12px;
    }
    .sitellm-sources-list a:hover {
      text-decoration: underline;
    }
    body.sitellm-reading-locked {
      overflow: hidden !important;
    }
    .sitellm-book-backdrop {
      position: fixed;
      inset: 0;
      z-index: 999999;
      display: none;
      align-items: center;
      justify-content: center;
      padding: clamp(16px, 4vw, 48px);
      background: rgba(15, 23, 42, 0.58);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      transition: opacity 160ms ease;
      opacity: 0;
    }
    .sitellm-book-backdrop.show {
      display: flex;
      opacity: 1;
    }
    .sitellm-book-backdrop.hidden {
      display: none;
    }
    .sitellm-book-container {
      width: min(960px, 96vw);
      max-height: 88vh;
      background: linear-gradient(120deg, #fdf8ed, #f7f1df);
      color: #2f2611;
      border-radius: 28px;
      box-shadow: 0 32px 64px rgba(15, 23, 42, 0.34);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .sitellm-book-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 22px 32px 16px;
      font-size: 16px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: rgba(47, 38, 17, 0.7);
    }
    .sitellm-book-title {
      display: flex;
      align-items: baseline;
      gap: 10px;
      font-weight: 600;
    }
    .sitellm-book-title-text {
      font-size: clamp(18px, 2.4vw, 22px);
    }
    .sitellm-book-close {
      border: none;
      background: rgba(47, 38, 17, 0.08);
      color: rgba(47, 38, 17, 0.72);
      width: 36px;
      height: 36px;
      border-radius: 50%;
      font-size: 20px;
      line-height: 1;
      cursor: pointer;
      display: grid;
      place-items: center;
      transition: transform 140ms ease, background 140ms ease;
    }
    .sitellm-book-close:hover {
      transform: rotate(6deg) scale(1.05);
      background: rgba(47, 38, 17, 0.14);
    }
    .sitellm-book-body {
      flex: 1 1 auto;
      padding: 0 36px 28px;
      overflow-y: auto;
      column-gap: clamp(28px, 4vw, 48px);
      column-fill: balance;
    }
    @media (min-width: 1024px) {
      .sitellm-book-body {
        column-count: 2;
      }
    }
    .sitellm-book-body::-webkit-scrollbar {
      width: 10px;
    }
    .sitellm-book-body::-webkit-scrollbar-thumb {
      background: rgba(47, 38, 17, 0.24);
      border-radius: 12px;
    }
    .sitellm-book-body h2 {
      column-span: all;
      font-size: clamp(22px, 3vw, 28px);
      margin: 28px 0 12px;
      line-height: 1.25;
    }
    .sitellm-book-body p {
      font-size: clamp(16px, 1.8vw, 18px);
      line-height: 1.72;
      margin: 14px 0;
      text-align: justify;
      hyphens: auto;
    }
    .sitellm-book-body figure {
      column-span: all;
      margin: 18px auto;
      max-width: min(640px, 90%);
      text-align: center;
    }
    .sitellm-book-body figure img {
      width: 100%;
      border-radius: 16px;
      box-shadow: 0 18px 36px rgba(15, 23, 42, 0.16);
    }
    .sitellm-book-body figure figcaption {
      margin-top: 8px;
      font-size: 14px;
      color: rgba(47, 38, 17, 0.7);
    }
    .sitellm-book-source {
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: rgba(47, 38, 17, 0.58);
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .sitellm-book-source::before {
      content: 'Источник';
      font-weight: 600;
      color: rgba(47, 38, 17, 0.68);
    }
    .sitellm-book-source a {
      color: rgba(${accent}, 0.95);
      text-decoration: none;
      font-weight: 500;
    }
    .sitellm-book-source a:hover {
      text-decoration: underline;
    }
    .sitellm-book-summary {
      column-span: all;
      font-size: clamp(15px, 1.6vw, 17px);
      font-style: italic;
      color: rgba(47, 38, 17, 0.7);
      margin: 12px 0 8px;
    }
    .sitellm-book-empty {
      column-span: all;
      font-size: 16px;
      color: rgba(47, 38, 17, 0.7);
      margin: 24px 0;
    }
    .sitellm-book-nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 16px 32px 24px;
      background: rgba(255, 252, 244, 0.88);
      border-top: 1px solid rgba(47, 38, 17, 0.12);
    }
    .sitellm-book-progress {
      font-size: 14px;
      color: rgba(47, 38, 17, 0.7);
    }
    .sitellm-book-nav button {
      padding: 10px 18px;
      border-radius: 14px;
      border: 1px solid rgba(${accent}, 0.32);
      background: rgba(${accent}, 0.16);
      color: rgba(${accent}, 1);
      font-size: 13px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease;
    }
    .sitellm-book-nav button:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 10px 20px rgba(${accent}, 0.18);
    }
    .sitellm-book-nav button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      box-shadow: none;
    }
    @media (max-width: 768px) {
      .sitellm-book-container {
        width: min(640px, 94vw);
      }
      .sitellm-book-body {
        padding: 0 22px 24px;
        column-count: 1 !important;
      }
      .sitellm-book-nav {
        flex-direction: column;
        align-items: stretch;
      }
      .sitellm-book-nav button {
        width: 100%;
      }
    }
    @media (prefers-color-scheme: dark) {
      .sitellm-reading-panel {
        background: linear-gradient(150deg, rgba(26, 33, 51, 0.94), rgba(18, 24, 40, 0.92));
        border-color: rgba(${accent}, 0.26);
        box-shadow: 0 14px 30px rgba(4, 6, 12, 0.55), inset 0 0 0 1px rgba(64, 84, 196, 0.25);
        color: rgba(229, 237, 255, 0.92);
      }
      .sitellm-reading-page {
        background: rgba(29, 36, 54, 0.92);
        border-color: rgba(${accent}, 0.22);
        box-shadow: 0 18px 32px rgba(3, 5, 12, 0.45);
        color: rgba(229, 237, 255, 0.92);
      }
      .sitellm-book-backdrop {
        background: rgba(3, 6, 18, 0.78);
      }
      .sitellm-book-container {
        background: linear-gradient(125deg, #1b2235, #111826);
        color: rgba(234, 240, 255, 0.96);
        box-shadow: 0 36px 70px rgba(0, 0, 0, 0.65);
      }
      .sitellm-book-header {
        color: rgba(198, 206, 235, 0.82);
      }
      .sitellm-book-close {
        background: rgba(98, 114, 204, 0.16);
        color: rgba(226, 233, 255, 0.85);
      }
      .sitellm-book-close:hover {
        background: rgba(98, 114, 204, 0.28);
      }
      .sitellm-book-body::-webkit-scrollbar-thumb {
        background: rgba(120, 136, 204, 0.35);
      }
      .sitellm-book-body figure img {
        box-shadow: 0 24px 40px rgba(3, 7, 18, 0.55);
      }
      .sitellm-book-body figure figcaption {
        color: rgba(206, 214, 240, 0.78);
      }
      .sitellm-book-source {
        color: rgba(189, 202, 240, 0.74);
      }
      .sitellm-book-source::before {
        color: rgba(214, 221, 250, 0.82);
      }
      .sitellm-book-nav {
        background: rgba(20, 26, 40, 0.88);
        border-top: 1px solid rgba(96, 116, 196, 0.28);
      }
      .sitellm-book-nav button {
        border-color: rgba(${accent}, 0.38);
        background: rgba(${accent}, 0.22);
        color: rgba(239, 244, 255, 0.95);
      }
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

  function escapeAttribute(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function resolveBaseUrl(script) {
    const attr = script.dataset.baseUrl;
    if (attr) return attr.replace(/\/$/, '');
    try {
      const url = new URL(script.src);
      url.pathname = url.pathname.split('/').slice(0, -1).join('/') || '/';
      return url.origin;
    } catch (err) {
      return window.location.origin;
    }
  }

  function sessionKey(project) {
    const key = `sitellm-avatar-session-${project || 'default'}`;
    try {
      const cached = localStorage.getItem(key);
      if (cached) return cached;
      const generated = (crypto.randomUUID && crypto.randomUUID()) ||
        Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem(key, generated);
      return generated;
    } catch (err) {
      return Math.random().toString(36).slice(2);
    }
  }

  function supportsSpeechRecognition() {
    return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
  }

  function createRecognition(lang) {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) return null;
    const instance = new Ctor();
    instance.lang = lang;
    instance.interimResults = true;
    instance.continuous = true;
    instance.maxAlternatives = 1;
    return instance;
  }

  function buildUrl(base, project, session, question, channel, model, reading) {
    const params = new URLSearchParams({ question, session_id: session, channel });
    if (project) params.set('project', project);
    if (model) params.set('model', model);
    if (reading) params.set('reading', '1');
    return `${base}/api/v1/llm/chat?${params.toString()}`;
  }

  async function fetchProjectConfig(baseUrl, project) {
    if (!project) {
      return { enabled: true, model: null };
    }
    const normalizedBase = baseUrl.replace(/\/$/, '');
    const cacheKey = `${normalizedBase}|${project}`;
    if (projectConfigCache.has(cacheKey)) {
      return projectConfigCache.get(cacheKey);
    }
    const promise = (async () => {
      const url = `${normalizedBase}/api/v1/llm/project-config?project=${encodeURIComponent(project)}`;
      const resp = await fetch(url, { mode: 'cors' });
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const data = await resp.json();
      return {
        enabled: data.llm_voice_enabled !== false,
        model: data.llm_voice_model || null,
      };
    })()
      .catch((error) => {
        projectConfigCache.delete(cacheKey);
        throw error;
      });
    projectConfigCache.set(cacheKey, promise);
    return promise;
  }

  async function fetchReadingPages(baseUrl, project, options = {}) {
    if (!project) {
      return { pages: [], total: 0, has_more: false, limit: 0, offset: 0 };
    }
    const normalizedBase = baseUrl.replace(/\/$/, '');
    const params = new URLSearchParams({ project });
    if (Number.isFinite(options.limit) && options.limit > 0) {
      params.set('limit', String(Math.floor(options.limit)));
    }
    if (Number.isFinite(options.offset) && options.offset > 0) {
      params.set('offset', String(Math.floor(options.offset)));
    }
    if (options.includeHtml) {
      params.set('include_html', '1');
    }
    if (options.url) {
      params.set('url', options.url);
    }
    const url = `${normalizedBase}/api/v1/reading/pages?${params.toString()}`;
    const resp = await fetch(url, { mode: 'cors' });
    if (!resp.ok) {
      throw new Error(`Reading pages HTTP ${resp.status}`);
    }
    return resp.json();
  }

  function stripEmojis(input) {
    if (!input) return '';
    let cleaned = String(input);
    try {
      cleaned = cleaned.replace(/\p{Extended_Pictographic}/gu, '');
    } catch (_) {
      cleaned = cleaned.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, '');
    }
    cleaned = cleaned.replace(/[\u200D\uFE0F]/g, '');
    return cleaned;
  }

  function clampSpeechRate(value) {
    if (!Number.isFinite(value)) return BASE_SPEECH_RATE;
    return Math.min(2, Math.max(0.5, value));
  }

  function enhancePauses(input) {
    if (!input) return '';
    let result = input
      .replace(/([,;:])\s+/g, '$1 … ')
      .replace(/([!?])\s+(?=[A-ZА-ЯЁ])/g, '$1 … ')
      .replace(/\s+—\s+/g, ' — … ')
      .replace(/\.\s+/g, '. … ')
      .replace(/:\s+(?=[0-9A-Za-zА-Яа-я])/g, ': … ')
      .replace(/\n{2,}/g, ' … ')
      .replace(/\n+/g, ' ')
      .replace(/\!{2,}/g, '!')
      .replace(/\?{2,}/g, '?');
    const softPauseRe = /\b(и|но|а|однако|затем|далее|при этом)\b/gi;
    result = result.replace(softPauseRe, (match, word, offset, original) => {
      const lookahead = original.slice(offset + match.length, offset + match.length + 2);
      if (lookahead.includes('…')) {
        return match;
      }
      return `${match} …`;
    });
    result = result.replace(/\s+…/g, ' …');
    result = result.replace(/\s{2,}/g, ' ');
    return result;
  }

  function deriveSpeechProfile(text, baseRate) {
    const trimmed = (text || '').trim();
    const augmented = enhancePauses(trimmed);
    const normalizedBase = clampSpeechRate(baseRate);
    let rate = normalizedBase;
    let pitch = DEFAULT_SPEECH_PITCH + (1 - normalizedBase) * 0.12;

    const isQuestion = /\?$/.test(trimmed);
    const isExclamation = /!$/.test(trimmed);
    const hasEllipsis = /…$/.test(augmented);

    if (isQuestion) {
      pitch += 0.22;
      rate = clampSpeechRate(rate * 0.9);
    } else if (isExclamation) {
      pitch += 0.18;
      rate = clampSpeechRate(rate * 1.04);
    } else if (hasEllipsis) {
      rate = clampSpeechRate(rate * 0.88);
    }

    const sentenceCount = augmented.split(/(?:[.!?…]+)\s+/).filter(Boolean).length;
    if (sentenceCount > 2) {
      rate = clampSpeechRate(rate * 0.95);
      pitch -= 0.03;
    }

    const commaCount = (augmented.match(/,/g) || []).length;
    if (commaCount >= 3) {
      rate = clampSpeechRate(rate * 0.96);
    }

    const emphaticMatches = augmented.match(/\b[А-ЯЁA-Z]{3,}\b/g) || [];
    if (emphaticMatches.length) {
      pitch += Math.min(0.04 * emphaticMatches.length, 0.18);
    }

    const emotiveMatches = augmented.match(/\b(классно|отлично|рад|здорово|perfect|great|amazing)\b/gi) || [];
    if (emotiveMatches.length) {
      pitch += 0.08;
    }

    if (augmented.length > 220) {
      rate = clampSpeechRate(rate * 0.93);
    } else if (augmented.length < 80 && baseRate > 1.02) {
      pitch -= 0.04;
    }

    const drift = (Math.random() - 0.5) * 0.06;
    pitch = Math.min(2, Math.max(0.2, pitch + drift));

    return {
      text: augmented,
      rate,
      pitch,
    };
  }

  const BASE_SPEECH_RATE = 1.0;
  const DEFAULT_SPEECH_PITCH = 1.0;
  const DEFAULT_VOICE_HINT = 'Milena';

  let cachedVoices = [];

  function refreshVoices() {
    if (!('speechSynthesis' in window)) return;
    const voices = speechSynthesis.getVoices();
    if (voices && voices.length) {
      cachedVoices = voices;
    }
  }

  if ('speechSynthesis' in window) {
    refreshVoices();
    if (typeof speechSynthesis.addEventListener === 'function') {
      speechSynthesis.addEventListener('voiceschanged', refreshVoices);
    } else {
      const prev = speechSynthesis.onvoiceschanged;
      speechSynthesis.onvoiceschanged = (...args) => {
        refreshVoices();
        if (typeof prev === 'function') prev.apply(speechSynthesis, args);
      };
    }
  }

  function resolveVoice(voiceHint, lang) {
    if (!('speechSynthesis' in window)) return null;
    const voices = speechSynthesis.getVoices();
    const list = voices && voices.length ? voices : cachedVoices;
    if (!list || !list.length) return null;
    const normalizedHint = (voiceHint || '').trim().toLowerCase();
    const pleasantCandidates = [
      'milena',
      'alena',
      'vera',
      'siri',
      'anna',
      'natasha',
      'victoria',
      'vera (enhanced)',
      'google русский',
      'google us english',
      'microsoft svetlana online (natural) - russian (russia)',
      'microsoft daria online (natural) - russian (russia)',
      'microsoft artem online (natural) - russian (russia)',
    ];
    const premiumKeywords = ['natural', 'neural', 'online', 'premium', 'google', 'microsoft', 'yandex'];

    if (normalizedHint) {
      const direct = list.find((voice) => voice.name.toLowerCase() === normalizedHint);
      if (direct) return direct;
      const fuzzy = list.find((voice) => voice.name.toLowerCase().includes(normalizedHint));
      if (fuzzy) return fuzzy;
    }

    const langLower = (lang || '').trim().toLowerCase();
    const prefix = langLower ? langLower.split('-')[0] : '';
    const languageMatches = langLower
      ? list.filter((voice) => {
          const voiceLang = (voice.lang || '').toLowerCase();
          if (!voiceLang) return false;
          if (voiceLang === langLower) return true;
          return prefix && voiceLang.startsWith(prefix);
        })
      : [];

    if (languageMatches.length && normalizedHint) {
      const hintMatch = languageMatches.find((voice) => voice.name.toLowerCase().includes(normalizedHint));
      if (hintMatch) return hintMatch;
    }

    if (languageMatches.length) {
      const premiumLang = languageMatches.find((voice) => {
        const lower = voice.name.toLowerCase();
        return premiumKeywords.some((keyword) => lower.includes(keyword));
      });
      if (premiumLang) return premiumLang;
      const pleasantLang = languageMatches.find((voice) => pleasantCandidates.includes(voice.name.toLowerCase()));
      if (pleasantLang) return pleasantLang;
    }

    if (!normalizedHint) {
      const pleasant = list.find((voice) => pleasantCandidates.includes(voice.name.toLowerCase()));
      if (pleasant) return pleasant;
    }

    const premiumAny = list.find((voice) => {
      const lower = voice.name.toLowerCase();
      return premiumKeywords.some((keyword) => lower.includes(keyword));
    });
    if (premiumAny) return premiumAny;

    if (languageMatches.length) {
      return languageMatches[0];
    }

    return list[0] || null;
  }

  function init(script) {
    const baseUrl = resolveBaseUrl(script);
    const project = script.dataset.project || '';
    const accentRgb = hexToRgb(script.dataset.color || '#4f7cff');
    const avatarLabel = script.dataset.label || 'AI';
    const lang = script.dataset.lang || 'ru-RU';
    const datasetVoiceHint = (script.dataset.voice || '').trim();
    const voiceHint = datasetVoiceHint || DEFAULT_VOICE_HINT;
    const datasetVoiceModel = script.dataset.voiceModel || '';
    let readingMode = script.dataset.readingMode === '1';
    const datasetSpeechRateRaw = parseFloat(script.dataset.speechRate || '');
    const initialSpeechRate = Number.isFinite(datasetSpeechRateRaw)
      ? clampSpeechRate(datasetSpeechRateRaw)
      : BASE_SPEECH_RATE;
    let speechRate = initialSpeechRate;
    script.dataset.speechRate = speechRate.toFixed(2);
    let avatarName = script.dataset.avatarName || avatarLabel;
    const avatarCharacterRaw = (script.dataset.avatarCharacter || script.dataset.character || '').trim().toLowerCase();
    const avatarImage = (script.dataset.avatarImage || '').trim();
    const avatarAnimatedFlag = script.dataset.avatarAnimated === '1';
    const hasCustomCharacter = Boolean(avatarCharacterRaw && CHARACTER_PRESETS[avatarCharacterRaw]);
    const interactionModeRaw = (script.dataset.mode || script.dataset.interactionMode || '').trim().toLowerCase();
    const allowedModes = [MODE_TEXT, MODE_VOICE, MODE_AVATAR];
    let interactionMode = allowedModes.includes(interactionModeRaw) ? interactionModeRaw : '';
    if (!interactionMode) {
      interactionMode = (hasCustomCharacter || avatarAnimatedFlag || avatarImage) ? MODE_AVATAR : MODE_VOICE;
    }
    const modeSupportsVoice = interactionMode !== MODE_TEXT;
    const modeSupportsAvatar = interactionMode === MODE_AVATAR || avatarAnimatedFlag || !!avatarImage || hasCustomCharacter;
    const datasetFallbackCharacter = (script.dataset.avatarDefault || '').trim().toLowerCase();
    const fallbackCharacter = datasetFallbackCharacter && CHARACTER_PRESETS[datasetFallbackCharacter]
      ? datasetFallbackCharacter
      : (interactionMode === MODE_AVATAR && CHARACTER_PRESETS.luna ? 'luna' : 'nova');
    const characterKey = hasCustomCharacter ? avatarCharacterRaw : (modeSupportsAvatar ? fallbackCharacter : '');
    const wantsAnimatedAvatar = modeSupportsAvatar;
    if (!script.dataset.avatarName && characterKey && CHARACTER_PRESETS[characterKey]?.label) {
      avatarName = CHARACTER_PRESETS[characterKey].label;
    }
    const avatarAlt = script.dataset.avatarAlt || (characterKey && CHARACTER_PRESETS[characterKey]?.label) || 'AI avatar';
    const headline = script.dataset.headline || 'AI Consultant';
    const subheadline = script.dataset.subtitle || 'Talk to me using your voice';

    ensureStyles(accentRgb);

    const orientationRaw = (script.dataset.orientation || script.dataset.anchor || script.dataset.position || '').trim();
    let orientation = normalizeOrientation(orientationRaw);
    script.dataset.orientation = orientation;

    const widgetWrapper = document.createElement('div');
    widgetWrapper.className = 'sitellm-voice-wrapper';
    widgetWrapper.dataset.orientation = orientation;
    applyOrientationClass(widgetWrapper, orientation);

    const container = document.createElement('section');
    container.className = 'sitellm-voice-widget';
    container.dataset.mode = interactionMode;
    container.classList.add(`mode-${interactionMode}`);

    const header = document.createElement('div');
    header.className = 'sitellm-voice-header';
    header.innerHTML = `<div><strong>${headline}</strong><div>${subheadline}</div></div>`;

    const avatar = document.createElement('div');
    avatar.className = 'sitellm-voice-avatar';
    const micVisual = document.createElement('div');
    micVisual.className = 'sitellm-voice-visual mic';
    const voiceVisual = document.createElement('div');
    voiceVisual.className = 'sitellm-voice-visual voice';
    const avatarLabelEl = document.createElement('span');
    avatarLabelEl.className = 'sitellm-voice-avatar-label';
    avatarLabelEl.textContent = avatarLabel;
    avatar.appendChild(micVisual);
    avatar.appendChild(voiceVisual);
    avatar.appendChild(avatarLabelEl);

    if (!modeSupportsVoice) {
      micVisual.style.display = 'none';
      voiceVisual.style.display = 'none';
    }

    let activeSpeechCount = 0;

    function ensureCharacterBadge(text) {
      if (!wantsAnimatedAvatar) return null;
      let badge = avatar.querySelector('.sitellm-character-badge');
      if (!text) {
        if (badge) badge.remove();
        return null;
      }
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'sitellm-character-badge';
        avatar.appendChild(badge);
      }
      badge.textContent = text;
      return badge;
    }

    function renderCharacterAvatar() {
      if (!wantsAnimatedAvatar) return;
      avatar.classList.add('has-character');
      avatarLabelEl.textContent = avatarName;
      const existing = avatar.querySelector('.sitellm-character-wrapper');
      if (existing) existing.remove();
      const wrapper = document.createElement('div');
      wrapper.className = 'sitellm-character-wrapper';
      if (avatarImage) {
        const safeSrc = escapeAttribute(avatarImage);
        const safeAlt = escapeAttribute(avatarAlt);
        wrapper.innerHTML = `<img src="${safeSrc}" alt="${safeAlt}" loading="lazy" decoding="async">`;
        ensureCharacterBadge(avatarName);
      } else {
        const preset = CHARACTER_PRESETS[characterKey] || CHARACTER_PRESETS.nova;
        wrapper.innerHTML = preset.svg;
        ensureCharacterBadge(preset.label || avatarName);
      }
      avatar.insertBefore(wrapper, micVisual);
      updateAvatarTalkingState();
    }

    function updateAvatarTalkingState() {
      if (!wantsAnimatedAvatar) return;
      if (activeSpeechCount > 0) {
        avatar.classList.add('talking');
      } else {
        avatar.classList.remove('talking');
      }
    }

    const instanceApi = {
      element: container,
      wrapper: widgetWrapper,
      getMode: () => interactionMode,
      getCharacter: () => characterKey,
      getSpeechRate: () => speechRate,
      getOrientation: () => orientation,
      setOrientation: (value) => {
        const next = normalizeOrientation(value);
        orientation = next;
        script.dataset.orientation = next;
        widgetWrapper.dataset.orientation = next;
        applyOrientationClass(widgetWrapper, next);
        return orientation;
      },
      startVoiceCapture: () => {
        if (!modeSupportsVoice) {
          return false;
        }
        voiceSettings.enabled = true;
        voiceArmed = true;
        updateMicButton();
        beginListening();
        return true;
      },
      stopVoiceCapture: () => {
        if (!modeSupportsVoice) {
          return false;
        }
        deactivateVoice();
        return true;
      },
      enableReadingMode: () => {
        enableReadingMode();
      },
      disableReadingMode: () => {
        disableReadingMode();
      },
      setSpeechRate: (value) => {
        const next = clampSpeechRate(Number(value));
        speechRate = next;
        script.dataset.speechRate = next.toFixed(2);
        return speechRate;
      },
      speakTest: (text) => {
        if (!modeSupportsVoice) return false;
        const sample = (text || '').trim();
        if (!sample) return false;
        stopActiveSpeech();
        spokenChars = 0;
        speak(sample, lang, voiceSettings.voiceHint || voiceHint, { flush: true });
        return true;
      },
      destroy: () => {
        closeBookView();
        if (bookBackdrop) {
          bookBackdrop.remove();
          bookBackdrop = null;
          bookContainerNode = null;
          bookBody = null;
          bookTitleNode = null;
          bookTitleLabel = null;
          bookProgressNode = null;
          bookSourceNode = null;
          bookSourceLink = null;
          bookPrevBtn = null;
          bookNextBtn = null;
        }
        bookFocusRestore = null;
        unlockPageScroll();
        if (widgetWrapper.parentElement) {
          widgetWrapper.parentElement.removeChild(widgetWrapper);
        } else if (container.parentElement) {
          container.parentElement.removeChild(container);
        }
        destructionObserver.disconnect();
        unregisterInstance(instanceApi);
      },
    };

    const destructionObserver = new MutationObserver(() => {
      const wrapperInDom = !widgetWrapper || document.body.contains(widgetWrapper);
      if (!document.body.contains(container) || !wrapperInDom) {
        instanceApi.destroy();
        destructionObserver.disconnect();
      }
    });
    destructionObserver.observe(document.body, { childList: true, subtree: true });
    registerInstance(instanceApi);

    if (wantsAnimatedAvatar) {
      renderCharacterAvatar();
    }
    header.appendChild(avatar);

    const status = document.createElement('div');
    status.className = 'sitellm-voice-status';
    status.innerHTML = modeSupportsVoice
      ? '<span class="bot">💬 Ready when you are</span>'
      : '<span class="bot">💬 Ready for your message</span>';
    if (readingMode) {
      const hint = document.createElement('span');
      hint.className = 'bot';
      hint.textContent = '📖 Reading mode enabled. Ask for the next page when you are ready.';
      status.appendChild(hint);
    }

    const readingPanel = document.createElement('section');
    readingPanel.className = 'sitellm-reading-panel';
    if (!readingMode) {
      readingPanel.classList.add('hidden');
    }
    const readingHeading = document.createElement('div');
    readingHeading.className = 'sitellm-reading-heading';
    const readingHeadingLabel = document.createElement('span');
    readingHeadingLabel.className = 'label';
    readingHeadingLabel.textContent = 'Материалы для чтения';
    const readingExpandBtn = document.createElement('button');
    readingExpandBtn.type = 'button';
    readingExpandBtn.className = 'sitellm-reading-expand';
    readingExpandBtn.textContent = 'Книжный режим';
    readingExpandBtn.title = 'Открыть книжный режим';
    readingExpandBtn.setAttribute('aria-haspopup', 'dialog');
    readingExpandBtn.setAttribute('aria-expanded', 'false');
    if (!readingMode) {
      readingExpandBtn.disabled = true;
      readingExpandBtn.style.display = 'none';
    }
    readingHeading.appendChild(readingHeadingLabel);
    readingHeading.appendChild(readingExpandBtn);
    const readingPlaceholder = document.createElement('div');
    readingPlaceholder.className = 'sitellm-reading-placeholder';
    readingPlaceholder.textContent = readingMode
      ? 'Загружаем страницы…'
      : 'Режим чтения появится после активации.';
    const readingScroll = document.createElement('div');
    readingScroll.className = 'sitellm-reading-scroll';
    const readingMoreBtn = document.createElement('button');
    readingMoreBtn.type = 'button';
    readingMoreBtn.className = 'sitellm-reading-more';
    readingMoreBtn.textContent = 'Ещё страницы';
    readingMoreBtn.style.display = 'none';
    readingPanel.appendChild(readingHeading);
    readingPanel.appendChild(readingPlaceholder);
    readingPanel.appendChild(readingScroll);
    readingPanel.appendChild(readingMoreBtn);

    readingExpandBtn.addEventListener('click', () => openBookView(readingState.currentIndex));

    const sourcesPanel = document.createElement('section');
    sourcesPanel.className = 'sitellm-sources-panel';
    const sourcesHeading = document.createElement('div');
    sourcesHeading.className = 'sitellm-sources-title';
    sourcesHeading.textContent = 'Источники';
    const sourcesList = document.createElement('div');
    sourcesList.className = 'sitellm-sources-list';
    sourcesPanel.appendChild(sourcesHeading);
    sourcesPanel.appendChild(sourcesList);

    const errorBox = document.createElement('div');
    errorBox.className = 'sitellm-voice-error';

    const actions = document.createElement('div');
    actions.className = 'sitellm-voice-actions';

    const micButton = document.createElement('button');
    micButton.className = 'sitellm-voice-mic';
    micButton.type = 'button';
    micButton.innerHTML = '🎤';

    if (!modeSupportsVoice) {
      micButton.style.display = 'none';
    }

    const transcript = document.createElement('div');
    transcript.className = 'sitellm-voice-transcript';
    transcript.textContent = modeSupportsVoice
      ? 'Tap the microphone and ask your question.'
      : 'Type a question below to start chatting.';

    actions.appendChild(micButton);
    actions.appendChild(transcript);

    const manualInput = document.createElement('div');
    manualInput.className = 'sitellm-voice-input';
    manualInput.innerHTML = `
      <textarea placeholder="Type your question if voice input is unavailable..."></textarea>
      <button type="button">Send</button>
    `;

    const content = document.createElement('div');
    content.className = 'sitellm-voice-content';
    content.appendChild(status);
    content.appendChild(readingPanel);
    content.appendChild(sourcesPanel);
    content.appendChild(actions);
    content.appendChild(manualInput);
    content.appendChild(errorBox);

    container.appendChild(header);
    container.appendChild(content);

    widgetWrapper.appendChild(container);
    script.insertAdjacentElement('beforebegin', widgetWrapper);

    const manualTextarea = manualInput.querySelector('textarea');
    const manualButton = manualInput.querySelector('button');

    const session = sessionKey(project);
    const channel = modeSupportsVoice ? 'voice-avatar' : 'widget';

    let recognition = modeSupportsVoice && supportsSpeechRecognition() ? createRecognition(lang) : null;
    let currentSource = null;
    const voiceSettings = {
      enabled: modeSupportsVoice,
      model: datasetVoiceModel,
      voiceHint,
      reading: readingMode,
    };
    let spokenChars = 0;

    const readingState = {
      offset: 0,
      pages: [],
      hasMore: true,
      loading: false,
      currentIndex: 0,
      project: project,
      sourceProject: project || null,
      referenceUrl: null,
      crossProject: null,
      notice: null,
      startOffset: 0,
      total: 0,
    };

    updateReadingUiState();

    function updateReadingUiState() {
      if (!readingPanel) return;
      if (readingMode) {
        readingPanel.classList.remove('hidden');
        if (readingExpandBtn) {
          readingExpandBtn.style.display = '';
          readingExpandBtn.disabled = false;
        }
        if (readingMoreBtn) {
          readingMoreBtn.style.display = readingState.hasMore ? 'inline-flex' : 'none';
          readingMoreBtn.disabled = !readingState.hasMore || readingState.loading;
        }
      } else {
        readingPanel.classList.add('hidden');
        if (readingExpandBtn) {
          readingExpandBtn.disabled = true;
          readingExpandBtn.style.display = 'none';
        }
        if (readingMoreBtn) {
          readingMoreBtn.style.display = 'none';
          readingMoreBtn.disabled = true;
        }
      }
    }

    function enableReadingMode() {
      if (readingMode) return;
      readingMode = true;
      voiceSettings.reading = true;
      updateReadingUiState();
    }

    function disableReadingMode(options = {}) {
      const { clearPages = true } = options;
      if (!readingMode && clearPages) {
        // still clear stale data even if already disabled
      }
      readingMode = false;
      voiceSettings.reading = false;
      if (clearPages) {
        readingState.pages = [];
        readingState.offset = 0;
        readingState.total = 0;
        readingState.currentIndex = 0;
        readingState.hasMore = false;
        readingState.loading = false;
        readingState.notice = null;
        readingState.crossProject = null;
        readingState.referenceUrl = null;
      }
      if (readingScroll && clearPages) {
        readingScroll.innerHTML = '';
      }
      if (readingPlaceholder) {
        readingPlaceholder.style.display = clearPages ? 'none' : readingPlaceholder.style.display;
      }
      updateReadingUiState();
    }

    function applyReadingData(entry) {
      if (!entry || typeof entry !== 'object') return;
      const pages = Array.isArray(entry.pages) ? entry.pages : [];
      if (!pages.length) return;
      readingState.loading = false;
      readingState.notice = null;
      readingState.crossProject = null;

      const projectCandidate = typeof entry.project === 'string' ? entry.project.trim() : '';
      let resolvedProject = projectCandidate;
      if (!resolvedProject) {
        const projectFromPages = pages.find((page) => page && typeof page.project === 'string' && page.project.trim());
        if (projectFromPages) {
          resolvedProject = projectFromPages.project.trim();
        }
      }
      if (resolvedProject) {
        readingState.project = resolvedProject;
        readingState.sourceProject = resolvedProject;
        if (project && resolvedProject !== project) {
          readingState.crossProject = resolvedProject;
        }
      } else if (!readingState.project) {
        readingState.notice = 'missing_project';
      }

      readingState.referenceUrl = null;
      const initialUrl = typeof entry.initialUrl === 'string' ? entry.initialUrl.trim() : '';
      if (initialUrl) {
        readingState.referenceUrl = initialUrl;
      } else {
        const pageWithUrl = pages.find((page) => page && typeof page.url === 'string' && page.url.trim());
        if (pageWithUrl) {
          readingState.referenceUrl = pageWithUrl.url.trim();
        }
      }
      if (!readingState.referenceUrl) {
        readingState.notice = readingState.notice || 'missing_url';
      }

      readingState.pages = pages;
      readingState.startOffset = Number.isFinite(entry.startOffset) ? Number(entry.startOffset) : 0;
      readingState.offset = readingState.startOffset + pages.length;
      readingState.total = Number.isFinite(entry.total) ? Number(entry.total) : pages.length;
      const hasMoreRaw = typeof entry.has_more !== 'undefined' ? entry.has_more : entry.hasMore;
      readingState.hasMore = Boolean(hasMoreRaw) && !readingState.notice;
      const desiredIndex = Number.isFinite(entry.initialIndex) ? Number(entry.initialIndex) : 0;
      readingState.currentIndex = Math.min(Math.max(desiredIndex, 0), Math.max(pages.length - 1, 0));
      enableReadingMode();
      renderReadingPages();
    }

    function clearSourcesPanel() {
      if (sourcesPanel) {
        sourcesPanel.classList.remove('show');
      }
      if (sourcesList) {
        sourcesList.innerHTML = '';
      }
    }

    function updateSourcesPanel(entries) {
      if (!sourcesPanel || !sourcesList) return;
      sourcesList.innerHTML = '';
      const valid = Array.isArray(entries) ? entries.filter((entry) => entry && entry.url) : [];
      if (!valid.length) {
        sourcesPanel.classList.remove('show');
        return;
      }
      valid.forEach((entry, index) => {
        const anchor = document.createElement('a');
        anchor.href = entry.url;
        anchor.target = '_blank';
        anchor.rel = 'noopener';
        anchor.textContent = entry.name || entry.url;
        anchor.dataset.index = String(index + 1);
        sourcesList.appendChild(anchor);
      });
      sourcesPanel.classList.add('show');
    }

    let bookBackdrop = null;
    let bookContainerNode = null;
    let bookBody = null;
    let bookTitleNode = null;
    let bookTitleLabel = null;
    let bookProgressNode = null;
    let bookSourceNode = null;
    let bookSourceLink = null;
    let bookPrevBtn = null;
    let bookNextBtn = null;
    let bookKeyHandler = null;
    let bookFocusRestore = null;

    function lockPageScroll() {
      const target = document.body;
      if (target) {
        target.classList.add('sitellm-reading-locked');
      }
    }

    function unlockPageScroll() {
      const target = document.body;
      if (target) {
        target.classList.remove('sitellm-reading-locked');
      }
    }

    function ensureBookOverlay() {
      if (bookBackdrop) return;

      bookBackdrop = document.createElement('div');
      bookBackdrop.className = 'sitellm-book-backdrop hidden';

      const container = document.createElement('div');
      container.className = 'sitellm-book-container';
      container.setAttribute('tabindex', '-1');
      container.setAttribute('role', 'dialog');
      container.setAttribute('aria-modal', 'true');
      bookOverlaySequence += 1;
      const overlayId = `sitellm-book-${bookOverlaySequence}`;
      container.dataset.overlayId = overlayId;
      container.setAttribute('aria-labelledby', `${overlayId}-title`);
      bookContainerNode = container;

      const bookHeader = document.createElement('header');
      bookHeader.className = 'sitellm-book-header';

      bookTitleNode = document.createElement('div');
      bookTitleNode.className = 'sitellm-book-title';

      bookTitleLabel = document.createElement('span');
      bookTitleLabel.className = 'sitellm-book-title-text';
      bookTitleLabel.textContent = 'Материалы для чтения';
      bookTitleLabel.id = `${overlayId}-title`;

      bookSourceNode = document.createElement('span');
      bookSourceNode.className = 'sitellm-book-source';
      bookSourceNode.style.display = 'none';
      bookSourceLink = document.createElement('a');
      bookSourceLink.target = '_blank';
      bookSourceLink.rel = 'noopener noreferrer';
      bookSourceLink.textContent = '';
      bookSourceNode.appendChild(bookSourceLink);

      bookTitleNode.appendChild(bookTitleLabel);
      bookTitleNode.appendChild(bookSourceNode);

      const bookCloseBtn = document.createElement('button');
      bookCloseBtn.type = 'button';
      bookCloseBtn.className = 'sitellm-book-close';
      bookCloseBtn.setAttribute('aria-label', 'Закрыть книжный режим');
      bookCloseBtn.textContent = '×';
      bookCloseBtn.addEventListener('click', () => closeBookView());

      bookHeader.appendChild(bookTitleNode);
      bookHeader.appendChild(bookCloseBtn);

      bookBody = document.createElement('div');
      bookBody.className = 'sitellm-book-body';

      const bookNav = document.createElement('footer');
      bookNav.className = 'sitellm-book-nav';

      bookPrevBtn = document.createElement('button');
      bookPrevBtn.type = 'button';
      bookPrevBtn.textContent = 'Предыдущая';
      bookPrevBtn.addEventListener('click', () => {
        showBookPage(readingState.currentIndex - 1);
      });

      bookProgressNode = document.createElement('div');
      bookProgressNode.className = 'sitellm-book-progress';
      bookProgressNode.textContent = 'Страница 0 из 0';

      bookNextBtn = document.createElement('button');
      bookNextBtn.type = 'button';
      bookNextBtn.textContent = 'Следующая';
      bookNextBtn.addEventListener('click', () => {
        showBookPage(readingState.currentIndex + 1);
      });

      bookNav.appendChild(bookPrevBtn);
      bookNav.appendChild(bookProgressNode);
      bookNav.appendChild(bookNextBtn);

      container.appendChild(bookHeader);
      container.appendChild(bookBody);
      container.appendChild(bookNav);

      bookBackdrop.appendChild(container);
      bookBackdrop.addEventListener('click', (event) => {
        if (event.target === bookBackdrop) {
          closeBookView();
        }
      });

      const host = document.body || document.documentElement;
      host.appendChild(bookBackdrop);
    }

    function resolveSourceMeta(rawUrl) {
      if (!rawUrl) return null;
      try {
        const resolved = new URL(rawUrl, baseUrl);
        const host = resolved.hostname.replace(/^www\./, '');
        let path = resolved.pathname || '';
        if (path.endsWith('/')) {
          path = path.slice(0, -1);
        }
        const query = resolved.search || '';
        let descriptor = host;
        if (path && path !== '/') {
          descriptor += path.length > 48 ? `${path.slice(0, 45)}…` : path;
        }
        if (query) {
          const shortQuery = query.length > 24 ? `${query.slice(0, 21)}…` : query;
          descriptor += shortQuery;
        }
        return {
          href: resolved.href,
          host,
          label: descriptor,
        };
      } catch (error) {
        console.debug('reading_source_parse_failed', error);
        return null;
      }
    }

    function updateBookProgressLabel() {
      if (!bookProgressNode) return;
      const totalCount = readingState.total && readingState.total >= readingState.pages.length
        ? readingState.total
        : readingState.pages.length;
      const labelValue = totalCount || readingState.pages.length;
      const totalLabel = labelValue
        ? `${labelValue}${readingState.hasMore ? '+' : ''}`
        : '0';
      const current = readingState.pages.length ? readingState.currentIndex + 1 : 0;
      bookProgressNode.textContent = `Страница ${current} из ${totalLabel}`;
    }

    function updateBookSource(page) {
      if (!bookSourceNode || !bookSourceLink) return;
      const meta = resolveSourceMeta(page?.url);
      if (meta) {
        bookSourceLink.href = meta.href;
        bookSourceLink.textContent = meta.label;
        bookSourceLink.title = meta.href;
        bookSourceNode.style.display = 'inline-flex';
      } else {
        bookSourceLink.removeAttribute('href');
        bookSourceLink.textContent = '';
        bookSourceLink.removeAttribute('title');
        bookSourceNode.style.display = 'none';
      }
    }

    function renderBookView() {
      if (!bookBackdrop || !bookBody || !bookTitleLabel) return;

      bookBody.innerHTML = '';

      if (!readingState.pages.length) {
        const placeholder = document.createElement('p');
        placeholder.className = 'sitellm-book-empty';
        placeholder.textContent = readingState.loading
          ? 'Загружаем страницы для чтения…'
          : 'Страницы появятся после завершения краулинга.';
        bookBody.appendChild(placeholder);
        bookTitleLabel.textContent = 'Материалы для чтения';
        updateBookProgressLabel();
        if (bookPrevBtn) bookPrevBtn.disabled = true;
        if (bookNextBtn) bookNextBtn.disabled = true;
        updateBookSource(null);
        return;
      }

      if (readingState.currentIndex >= readingState.pages.length) {
        readingState.currentIndex = Math.max(0, readingState.pages.length - 1);
      }

      const page = readingState.pages[readingState.currentIndex];
      const titleText = page?.title || `Страница ${page?.order ?? readingState.currentIndex + 1}`;
      bookTitleLabel.textContent = titleText;
      updateBookSource(page);

      if (readingState.crossProject && readingState.crossProject !== project) {
        const projectNotice = document.createElement('p');
        projectNotice.className = 'sitellm-book-notice';
        projectNotice.textContent = `Материалы относятся к проекту "${readingState.crossProject}".`;
        bookBody.appendChild(projectNotice);
      }

      if (readingState.notice === 'missing_project') {
        const projectWarning = document.createElement('p');
        projectWarning.className = 'sitellm-book-notice';
        projectWarning.textContent = 'Не удалось определить проект для загрузки дополнительных страниц.';
        bookBody.appendChild(projectWarning);
      }

      if (readingState.notice === 'missing_url') {
        const limitNotice = document.createElement('p');
        limitNotice.className = 'sitellm-book-notice';
        limitNotice.textContent = 'Дополнительные страницы недоступны для этого источника.';
        bookBody.appendChild(limitNotice);
      }

      if (page?.segments?.length) {
        page.segments.forEach((segment) => {
          if (!segment) return;
          if (segment.summary) {
            const summaryParagraph = document.createElement('p');
            summaryParagraph.className = 'sitellm-book-summary';
            summaryParagraph.textContent = segment.summary;
            bookBody.appendChild(summaryParagraph);
          }
          const textValue = typeof segment.text === 'string' ? segment.text : '';
          if (!textValue.trim()) return;
          textValue.split(/\n+/).map((p) => p.trim()).filter(Boolean).forEach((line) => {
            const paragraph = document.createElement('p');
            paragraph.textContent = line;
            bookBody.appendChild(paragraph);
          });
        });
      } else if (page?.text) {
        page.text.split(/\n+/).map((p) => p.trim()).filter(Boolean).forEach((line) => {
          const paragraph = document.createElement('p');
          paragraph.textContent = line;
          bookBody.appendChild(paragraph);
        });
      }

      if (Array.isArray(page?.images) && page.images.length) {
        page.images.forEach((image, index) => {
          if (!image || !image.url) return;
          const figure = document.createElement('figure');
          const img = document.createElement('img');
          img.loading = 'lazy';
          img.src = image.url;
          img.alt = image.caption || `Иллюстрация ${index + 1}`;
          figure.appendChild(img);
          if (image.caption) {
            const caption = document.createElement('figcaption');
            caption.textContent = image.caption;
            figure.appendChild(caption);
          }
          bookBody.appendChild(figure);
        });
      }

      updateBookProgressLabel();

      if (bookPrevBtn) {
        bookPrevBtn.disabled = readingState.currentIndex <= 0;
      }
      if (bookNextBtn) {
        const atLastLoaded = readingState.currentIndex >= readingState.pages.length - 1;
        bookNextBtn.disabled = (atLastLoaded && !readingState.hasMore) || readingState.loading;
      }
    }

    function closeBookView() {
      if (!bookBackdrop) return;
      bookBackdrop.classList.remove('show');
      unlockPageScroll();
      if (readingExpandBtn) {
        readingExpandBtn.setAttribute('aria-expanded', 'false');
      }
      window.setTimeout(() => {
        if (bookBackdrop) {
          bookBackdrop.classList.add('hidden');
        }
      }, 180);
      if (bookKeyHandler) {
        document.removeEventListener('keydown', bookKeyHandler);
        bookKeyHandler = null;
      }
      const restoreTarget = bookFocusRestore;
      bookFocusRestore = null;
      if (restoreTarget && typeof restoreTarget.focus === 'function') {
        window.setTimeout(() => {
          try {
            restoreTarget.focus({ preventScroll: true });
          } catch (err) {
            restoreTarget.focus();
          }
        }, 200);
      }
    }

    async function showBookPage(targetIndex) {
      if (targetIndex < 0) {
        readingState.currentIndex = 0;
        renderBookView();
        renderReadingPages();
        return;
      }

      if (targetIndex < readingState.pages.length) {
        readingState.currentIndex = targetIndex;
        renderBookView();
        renderReadingPages();
        return;
      }

      if (!readingState.hasMore || readingState.loading) {
        readingState.currentIndex = Math.max(0, readingState.pages.length - 1);
        renderBookView();
        renderReadingPages();
        return;
      }

      await loadReadingPages();
      if (targetIndex < readingState.pages.length) {
        readingState.currentIndex = targetIndex;
      } else if (readingState.pages.length) {
        readingState.currentIndex = readingState.pages.length - 1;
      }
      renderBookView();
      renderReadingPages();
    }

    async function openBookView(initialIndex = 0) {
      if (!readingMode) return;
      ensureBookOverlay();
      bookBackdrop.classList.remove('hidden');
      window.requestAnimationFrame(() => {
        if (bookBackdrop) {
          bookBackdrop.classList.add('show');
        }
      });
      if (readingExpandBtn) {
        readingExpandBtn.setAttribute('aria-expanded', 'true');
      }
      lockPageScroll();

      if (document.activeElement && typeof document.activeElement.focus === 'function') {
        bookFocusRestore = document.activeElement;
      } else {
        bookFocusRestore = null;
      }

      if (!readingState.pages.length && !readingState.loading) {
        await loadReadingPages({ reset: false });
      }

      if (readingState.pages.length) {
        readingState.currentIndex = Math.min(Math.max(initialIndex, 0), readingState.pages.length - 1);
      } else {
        readingState.currentIndex = 0;
      }

      renderBookView();
      renderReadingPages();

      if (bookContainerNode && typeof bookContainerNode.focus === 'function') {
        try {
          bookContainerNode.focus({ preventScroll: true });
        } catch (err) {
          bookContainerNode.focus();
        }
      }

      if (!bookKeyHandler) {
        bookKeyHandler = (event) => {
          if (event.key === 'Escape') {
            event.preventDefault();
            closeBookView();
            return;
          }
          if (event.key === 'ArrowRight') {
            event.preventDefault();
            showBookPage(readingState.currentIndex + 1);
          } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            showBookPage(readingState.currentIndex - 1);
          }
        };
        document.addEventListener('keydown', bookKeyHandler);
      }
    }

    function renderReadingPages() {
      readingScroll.innerHTML = '';
      const items = Array.isArray(readingState.pages) ? readingState.pages : [];
      if (!items.length) {
        readingState.currentIndex = 0;
      } else if (readingState.currentIndex >= items.length) {
        readingState.currentIndex = Math.max(0, items.length - 1);
      }
      items.forEach((page, index) => {
        const pageEl = document.createElement('article');
        pageEl.className = 'sitellm-reading-page';
        pageEl.setAttribute('role', 'button');
        pageEl.tabIndex = 0;
        if (index === readingState.currentIndex) {
          pageEl.classList.add('active');
        }
        const headingEl = document.createElement('h4');
        const orderLabel = typeof page?.order === 'number' ? page.order : index + 1;
        headingEl.textContent = page?.title || `Страница ${orderLabel}`;
        pageEl.appendChild(headingEl);

        const sourceMeta = resolveSourceMeta(page?.url);
        if (sourceMeta) {
          const sourceEl = document.createElement('div');
          sourceEl.className = 'sitellm-reading-source';
          const link = document.createElement('a');
          link.href = sourceMeta.href;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = sourceMeta.label;
          link.title = sourceMeta.href;
          sourceEl.appendChild(link);
          pageEl.appendChild(sourceEl);
        }

        const segments = Array.isArray(page?.segments) && page.segments.length ? page.segments : null;
        if (segments) {
          segments.forEach((segment) => {
            const textValue = typeof segment?.text === 'string' ? segment.text : '';
            const summaryValue = typeof segment?.summary === 'string' ? segment.summary : '';
            if (!textValue.trim() && !summaryValue.trim()) return;
            const segmentEl = document.createElement('div');
            segmentEl.className = 'sitellm-reading-segment';
            if (summaryValue.trim()) {
              const summaryEl = document.createElement('div');
              summaryEl.className = 'sitellm-reading-page-summary';
              summaryEl.textContent = summaryValue.trim();
              segmentEl.appendChild(summaryEl);
            }
            const blocks = textValue.split(/\n{2,}/);
            blocks.forEach((block) => {
              const trimmed = block.trim();
              if (!trimmed) return;
              const paragraph = document.createElement('p');
              paragraph.textContent = trimmed;
              segmentEl.appendChild(paragraph);
            });
            if (segmentEl.children.length) {
              pageEl.appendChild(segmentEl);
            }
          });
        } else if (typeof page?.text === 'string' && page.text.trim()) {
          const segmentEl = document.createElement('div');
          segmentEl.className = 'sitellm-reading-segment';
          page.text.split(/\n{2,}/).forEach((block) => {
            const trimmed = block.trim();
            if (!trimmed) return;
            const paragraph = document.createElement('p');
            paragraph.textContent = trimmed;
            segmentEl.appendChild(paragraph);
          });
          if (segmentEl.children.length) {
            pageEl.appendChild(segmentEl);
          }
        }

        const images = Array.isArray(page?.images) ? page.images : [];
        if (images.length) {
          const imagesEl = document.createElement('div');
          imagesEl.className = 'sitellm-reading-images';
          images.forEach((image) => {
            const source = typeof image?.url === 'string' && image.url ? image.url : null;
            if (!source) return;
            const img = document.createElement('img');
            img.src = source;
            img.alt = `Иллюстрация ${page?.title || ''}`.trim() || 'Иллюстрация';
            img.loading = 'lazy';
            imagesEl.appendChild(img);
          });
          if (imagesEl.children.length) {
            pageEl.appendChild(imagesEl);
          }
        }

        pageEl.addEventListener('click', () => {
          openBookView(index);
        });
        pageEl.addEventListener('keydown', (event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            openBookView(index);
          }
          if (event.key === 'ArrowRight') {
            event.preventDefault();
            showBookPage(readingState.currentIndex + 1);
          }
          if (event.key === 'ArrowLeft') {
            event.preventDefault();
            showBookPage(readingState.currentIndex - 1);
          }
        });

        readingScroll.appendChild(pageEl);
      });

      if (items.length) {
        readingPlaceholder.style.display = 'none';
      } else {
        readingPlaceholder.style.display = 'block';
        let placeholderMessage;
        if (readingState.notice === 'missing_project') {
          placeholderMessage = 'Не удалось определить проект для режима чтения.';
        } else if (readingState.notice === 'missing_url') {
          placeholderMessage = 'Источник не содержит ссылки для дополнительных страниц.';
        } else if (readingState.loading) {
          placeholderMessage = 'Загружаем страницы…';
        } else if (readingMode) {
          placeholderMessage = 'Материалы для чтения появятся после краулинга.';
        } else {
          placeholderMessage = 'Режим чтения не активирован.';
        }
        if (readingState.crossProject && readingState.crossProject !== project) {
          placeholderMessage = `${placeholderMessage} Материалы относятся к проекту "${readingState.crossProject}".`;
        }
        readingPlaceholder.textContent = placeholderMessage;
      }

      updateReadingUiState();
      renderBookView();
    }

    async function loadReadingPages({ reset = false } = {}) {
      if (!readingMode) {
        return;
      }

      if (!readingState.project) {
        readingState.project = project;
      }

      if (!readingState.project) {
        readingPlaceholder.style.display = 'block';
        readingPlaceholder.textContent = 'Укажите проект, чтобы получить материалы для чтения.';
        readingState.hasMore = false;
        updateReadingUiState();
        return;
      }

      if (readingState.notice === 'missing_project' || readingState.notice === 'missing_url') {
        readingPlaceholder.style.display = 'block';
        readingPlaceholder.textContent = readingState.notice === 'missing_project'
          ? 'Не удалось определить проект для режима чтения.'
          : 'Источник не содержит ссылки для дополнительных страниц.';
        readingState.hasMore = false;
        updateReadingUiState();
        return;
      }

      if (readingState.loading) return;
      if (!readingState.hasMore && !reset && readingState.pages.length) {
        return;
      }

      if (reset) {
        readingState.offset = 0;
        readingState.pages = [];
        readingState.hasMore = true;
        readingState.currentIndex = 0;
        readingState.startOffset = 0;
        readingState.total = 0;
        readingState.notice = null;
        readingState.crossProject = null;
        readingState.referenceUrl = null;
        readingState.sourceProject = readingState.project || project || null;
      }

      readingState.loading = true;
      readingPlaceholder.style.display = 'block';
      readingPlaceholder.textContent = readingState.pages.length ? 'Обновляем…' : 'Загружаем страницы…';
      updateReadingUiState();

      try {
        const data = await fetchReadingPages(baseUrl, readingState.project, {
          limit: 5,
          offset: readingState.offset,
        });
        const newPages = Array.isArray(data?.pages) ? data.pages : [];
        if (readingState.offset === 0 || reset) {
          readingState.pages = newPages;
          readingState.currentIndex = 0;
        } else if (newPages.length) {
          readingState.pages = readingState.pages.concat(newPages);
        }
        readingState.offset = readingState.pages.length;
        readingState.hasMore = Boolean(data?.has_more);
        if (typeof data?.total === 'number' && data.total >= 0) {
          readingState.total = data.total;
        }
        renderReadingPages();
      } catch (error) {
        console.error(error);
        readingPlaceholder.style.display = 'block';
        readingPlaceholder.textContent = 'Не удалось загрузить страницы для чтения.';
        readingState.hasMore = false;
        renderBookView();
      } finally {
        readingState.loading = false;
        updateReadingUiState();
      }
    }

    readingMoreBtn.addEventListener('click', () => loadReadingPages());

    const IDLE_TIMEOUT_MS = 90000;
    let voiceArmed = false;
    let listening = false;
    let idleTimer = null;
    let recognitionBound = false;
    let currentUtterance = null;
    let awaitingResponse = false;
    let lastFinalUtterance = '';
    let recognitionPausedBySpeech = false;
    let recognitionMuteUntil = 0;

    function clearIdleTimer() {
      if (idleTimer) {
        clearTimeout(idleTimer);
        idleTimer = null;
      }
    }

    function updateMicButton() {
      if (!modeSupportsVoice) {
        micButton.style.display = 'none';
        micButton.disabled = true;
        return;
      }
      if (!voiceSettings.enabled) {
        micButton.disabled = true;
        micButton.classList.remove('active');
        micButton.textContent = '🎤';
        return;
      }
      micButton.style.display = '';
      micButton.disabled = false;
      if (voiceArmed) {
        micButton.classList.add('active');
        micButton.textContent = listening ? '⏺' : '⏸';
      } else {
        micButton.classList.remove('active');
        micButton.textContent = '🎤';
      }
    }

    function renewIdleTimer() {
      clearIdleTimer();
      if (!voiceArmed || !modeSupportsVoice) return;
      idleTimer = window.setTimeout(() => {
        if (!voiceArmed) return;
        deactivateVoice('Voice assistant paused due to inactivity.');
        appendMessage('bot', '💤 Voice assistant paused due to inactivity');
      }, IDLE_TIMEOUT_MS);
    }

    function stopRecognitionInternal() {
      if (!modeSupportsVoice) {
        listening = false;
        return;
      }
      listening = false;
      updateMicButton();
      stopMicMonitor();
      if (recognition) {
        try {
          recognition.stop();
        } catch (_) {}
        try {
          recognition.abort();
        } catch (_) {}
      }
      recognitionMuteUntil = Date.now() + 400;
    }

    function bindRecognitionListeners() {
      if (!modeSupportsVoice || !recognition || recognitionBound) return;
      recognitionBound = true;

      recognition.addEventListener('result', (event) => {
        renewIdleTimer();
        if (!event.results || event.results.length === 0) {
          return;
        }
        let interimBuffer = '';
        let finalBuffer = '';
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const res = event.results[i];
          const fragment = (res[0] && res[0].transcript) ? res[0].transcript : '';
          if (!fragment) continue;
          if (res.isFinal) {
            finalBuffer += fragment;
          } else {
            interimBuffer += fragment;
          }
        }
        const interimClean = stripEmojis(interimBuffer).trim();
        if (interimClean && !finalBuffer) {
          transcript.textContent = interimClean;
        }
        const finalClean = stripEmojis(finalBuffer).trim();
        if (!finalClean) {
          return;
        }
        if (finalClean === lastFinalUtterance) {
          return;
        }
        const now = Date.now();
        if (now < recognitionMuteUntil) {
          return;
        }
        if (isEchoOfAssistant(finalClean)) {
          lastFinalUtterance = finalClean;
          transcript.textContent = 'Listening paused to avoid echo.';
          appendMessage('bot', '🔇 Ignored playback captured by the microphone.');
          resumeAfterResponse();
          return;
        }
        if (awaitingResponse) {
          if (containsInterruptCommand(finalClean)) {
            recognitionMuteUntil = Date.now() + 800;
            stopActiveSpeech();
            awaitingResponse = false;
            appendMessage('bot', '⏹️ Assistant speech interrupted by user command.');
            transcript.textContent = 'Assistant paused.';
            renewIdleTimer();
          } else {
            recognitionMuteUntil = Date.now() + 600;
            transcript.textContent = 'Assistant is responding...';
            lastFinalUtterance = finalClean;
          }
          return;
        }
        recognitionMuteUntil = Date.now() + 600;
        lastFinalUtterance = finalClean;
        transcript.textContent = finalClean;
        stopActiveSpeech();
        handleQuestion(finalClean);
      });

      recognition.addEventListener('error', (event) => {
        const message = `Voice input error: ${event.error || 'unknown'}`;
        setError(message);
        listening = false;
        updateMicButton();
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          deactivateVoice('Microphone access is blocked. Use the text form below.');
          manualInput.style.display = 'block';
          return;
        }
        if (voiceArmed) {
          setTimeout(() => {
            if (voiceArmed && !listening) {
              beginListening();
            }
          }, 800);
        }
      });

      recognition.addEventListener('end', () => {
        listening = false;
        updateMicButton();
        if (!modeSupportsVoice || recognitionPausedBySpeech) {
          return;
        }
        if (voiceArmed) {
          setTimeout(() => {
            if (voiceArmed && !listening) {
              beginListening();
            }
          }, 250);
        }
      });
    }

    function beginListening() {
      if (!modeSupportsVoice || !voiceSettings.enabled) {
        return;
      }
      if (!recognition) return;
      bindRecognitionListeners();
      if (listening) return;
      listening = true;
      updateMicButton();
      startMicMonitor();
      try {
        recognition.start();
      } catch (err) {
        listening = false;
        updateMicButton();
        if (!err || err.name !== 'InvalidStateError') {
          setError('Unable to access microphone.');
          deactivateVoice();
          manualInput.style.display = 'block';
        }
      }
    }

    function deactivateVoice(message) {
      voiceArmed = false;
      clearIdleTimer();
      awaitingResponse = false;
      lastFinalUtterance = '';
      cancelStream();
      stopActiveSpeech();
      stopRecognitionInternal();
      recognitionPausedBySpeech = false;
      activeSpeechCount = 0;
      assistantUtteranceHistory.length = 0;
      if (message) setError(message); else setError('');
      transcript.textContent = modeSupportsVoice
        ? 'Tap the microphone and ask your question.'
        : 'Type a question below to start chatting.';
      updateAvatarTalkingState();
    }

    function resumeAfterResponse() {
      renewIdleTimer();
    }

    function resetSpeechStream() {
      spokenChars = 0;
      if (!modeSupportsVoice) {
        currentUtterance = null;
        activeSpeechCount = 0;
        return;
      }
      if ('speechSynthesis' in window) {
        try { speechSynthesis.cancel(); } catch (_) {}
      }
      currentUtterance = null;
      activeSpeechCount = 0;
      recognitionMuteUntil = Date.now() + 600;
      resumeRecognitionIfPaused(0);
      updateAvatarTalkingState();
    }

    function stopActiveSpeech() {
      if (!modeSupportsVoice || !('speechSynthesis' in window)) return;
      currentUtterance = null;
      awaitingResponse = false;
      activeSpeechCount = 0;
      stopVoiceVisualizer();
      try {
        speechSynthesis.cancel();
      } catch (_) {}
      recognitionMuteUntil = Date.now() + 600;
      resumeRecognitionIfPaused(0);
      updateAvatarTalkingState();
    }

    function resumeRecognitionIfPaused(delay = 160) {
      if (!modeSupportsVoice) {
        recognitionPausedBySpeech = false;
        return;
      }
      if (!recognitionPausedBySpeech) {
        return;
      }
      if (!voiceArmed || !recognition) {
        recognitionPausedBySpeech = false;
        return;
      }
      if (activeSpeechCount > 0) {
        return;
      }
      const attemptResume = () => {
        if (!voiceArmed || activeSpeechCount > 0) {
          return;
        }
        if (listening) {
          recognitionPausedBySpeech = false;
          return;
        }
        recognitionPausedBySpeech = false;
        beginListening();
      };
      if (delay > 0) {
        setTimeout(attemptResume, delay);
      } else {
        attemptResume();
      }
    }

    function setError(message) {
      if (!message) {
        errorBox.textContent = '';
        errorBox.classList.remove('show');
      } else {
        errorBox.textContent = message;
        errorBox.classList.add('show');
      }
    }

    function appendMessage(role, text) {
      const span = document.createElement('span');
      span.className = role;
      span.textContent = text;
      status.appendChild(span);
      const maxChildren = 6;
      while (status.children.length > maxChildren) {
        status.removeChild(status.firstChild);
      }
    }

    const micMonitor = {
      stream: null,
      ctx: null,
      analyser: null,
      data: null,
      raf: null,
      failed: false,
    };

    const voicePulse = {
      raf: null,
      phase: 0,
    };

    function startVoiceVisualizer() {
      if (!modeSupportsVoice || !voiceVisual) return;
      stopVoiceVisualizer();
      voiceVisual.classList.add('active');
      const tick = () => {
        voicePulse.phase += 0.08;
        const level = (Math.sin(voicePulse.phase) + 1) / 2;
        voiceVisual.style.transform = `scale(${1 + level * 0.28})`;
        voiceVisual.style.opacity = `${0.55 + level * 0.35}`;
        voicePulse.raf = requestAnimationFrame(tick);
      };
      tick();
    }

    function stopVoiceVisualizer() {
      if (voicePulse.raf) cancelAnimationFrame(voicePulse.raf);
      voicePulse.raf = null;
      if (voiceVisual) {
        voiceVisual.classList.remove('active');
        voiceVisual.style.transform = 'scale(1)';
        voiceVisual.style.opacity = '0';
      }
      if (activeSpeechCount === 0) {
        updateAvatarTalkingState();
      }
    }

    function speak(text, lang, voiceHint, options = {}) {
      if (!modeSupportsVoice) {
        return;
      }
      if (!('speechSynthesis' in window)) return;
      const {
        flush = true,
        rate = speechRate,
        pitch = DEFAULT_SPEECH_PITCH,
        voiceOverride,
      } = options;
      const sanitized = stripEmojis(text);
      if (!sanitized.trim()) return;
      const profile = deriveSpeechProfile(sanitized, rate);
      if (voiceArmed && activeSpeechCount === 0) {
        stopRecognitionInternal();
        recognitionPausedBySpeech = true;
        recognitionMuteUntil = Date.now() + 1000;
      }
      const utterance = new SpeechSynthesisUtterance(profile.text);
      if (lang) utterance.lang = lang;
      utterance.rate = profile.rate;
      utterance.pitch = profile.pitch;
      utterance.volume = 0.95;
      const selectedVoice = resolveVoice(voiceOverride || voiceHint, lang);
      if (selectedVoice) {
        utterance.voice = selectedVoice;
      }
      if (flush) {
        try {
          speechSynthesis.cancel();
        } catch (_) {}
      }
      currentUtterance = utterance;
      stopVoiceVisualizer();
      startVoiceVisualizer();
      activeSpeechCount += 1;
      updateAvatarTalkingState();
      utterance.onstart = () => {
        recognitionMuteUntil = Date.now() + 1200;
      };
      utterance.onend = () => {
        activeSpeechCount = Math.max(0, activeSpeechCount - 1);
        currentUtterance = null;
        awaitingResponse = false;
        stopVoiceVisualizer();
        recognitionMuteUntil = Date.now() + 600;
        if (activeSpeechCount === 0) {
          resumeRecognitionIfPaused();
          renewIdleTimer();
        }
        updateAvatarTalkingState();
      };
      utterance.onerror = () => {
        activeSpeechCount = Math.max(0, activeSpeechCount - 1);
        currentUtterance = null;
        stopVoiceVisualizer();
        recognitionMuteUntil = Date.now() + 600;
        if (activeSpeechCount === 0) {
          resumeRecognitionIfPaused(0);
        }
        updateAvatarTalkingState();
      };
      try {
        speechSynthesis.speak(utterance);
      } catch (error) {
        activeSpeechCount = Math.max(0, activeSpeechCount - 1);
        currentUtterance = null;
        awaitingResponse = false;
        stopVoiceVisualizer();
        console.warn('voice_avatar_tts_failed', error);
        recognitionMuteUntil = Date.now() + 600;
        resumeRecognitionIfPaused(0);
        updateAvatarTalkingState();
      }
    }

    function applyMicLevel(level) {
      if (!modeSupportsVoice || !micVisual) return;
      micVisual.classList.add('active');
      micVisual.style.transform = `scale(${1 + Math.min(0.6, level * 0.6)})`;
      micVisual.style.opacity = `${Math.min(0.95, 0.25 + level * 1.3)}`;
    }

    async function startMicMonitor() {
      if (!modeSupportsVoice || !micVisual || !navigator.mediaDevices?.getUserMedia || micMonitor.failed) return;
      try {
        if (!micMonitor.stream) {
          micMonitor.stream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: { ideal: true },
              noiseSuppression: { ideal: true },
              autoGainControl: { ideal: false },
              channelCount: { ideal: 1 },
              sampleRate: { ideal: 44100 },
              latency: { ideal: 0.02 },
            },
          });
          micMonitor.ctx = new (window.AudioContext || window.webkitAudioContext)();
          const source = micMonitor.ctx.createMediaStreamSource(micMonitor.stream);
          micMonitor.analyser = micMonitor.ctx.createAnalyser();
          micMonitor.analyser.fftSize = 512;
          micMonitor.analyser.smoothingTimeConstant = 0.7;
          micMonitor.data = new Uint8Array(micMonitor.analyser.fftSize);
          source.connect(micMonitor.analyser);
        }
        if (micMonitor.ctx && micMonitor.ctx.state === 'suspended') {
          await micMonitor.ctx.resume();
        }
        if (micMonitor.raf) cancelAnimationFrame(micMonitor.raf);
        const tick = () => {
          if (!micMonitor.analyser) return;
          micMonitor.analyser.getByteTimeDomainData(micMonitor.data);
          let sum = 0;
          for (let i = 0; i < micMonitor.data.length; i += 1) {
            const value = (micMonitor.data[i] - 128) / 128;
            sum += value * value;
          }
          const rms = Math.sqrt(sum / micMonitor.data.length);
          const level = Math.min(1, rms * 3.5);
          applyMicLevel(level);
          micMonitor.raf = requestAnimationFrame(tick);
        };
        tick();
      } catch (error) {
        micMonitor.failed = true;
        console.warn('voice_avatar_mic_visualizer_failed', error);
      }
    }

    function stopMicMonitor() {
      if (micMonitor.raf) cancelAnimationFrame(micMonitor.raf);
      micMonitor.raf = null;
      if (micVisual) {
        micVisual.classList.remove('active');
        micVisual.style.transform = 'scale(1)';
        micVisual.style.opacity = '0';
      }
      if (micMonitor.ctx && micMonitor.ctx.state !== 'closed') {
        micMonitor.ctx.suspend().catch(() => {});
      }
    }

    const disabledMessage = 'Voice assistant is disabled by the administrator.';
    let modelAnnounced = false;

    function announceModel(model) {
      if (!model || modelAnnounced) return;
      appendMessage('bot', `⚙️ Model: ${model}`);
      modelAnnounced = true;
    }

    const normalizedBase = baseUrl.replace(/\/$/, '');
    if (project) {
      if (modeSupportsVoice) {
        micButton.disabled = true;
      }
      if (modeSupportsVoice) {
        manualButton.disabled = true;
        if (manualTextarea) manualTextarea.disabled = true;
      }
      fetchProjectConfig(normalizedBase, project)
        .then((cfg) => {
          voiceSettings.enabled = modeSupportsVoice ? cfg.enabled : true;
          if (cfg.model) {
            voiceSettings.model = cfg.model;
          }
          if (modeSupportsVoice && !voiceSettings.enabled) {
            micButton.disabled = true;
            deactivateVoice(disabledMessage);
            micButton.textContent = '🔇';
            status.innerHTML = '';
            appendMessage('bot', disabledMessage);
            setError(disabledMessage);
            manualButton.disabled = true;
            if (manualTextarea) manualTextarea.disabled = true;
            manualInput.style.display = 'block';
            return;
          }
          micButton.disabled = false;
          voiceArmed = false;
          updateMicButton();
          manualButton.disabled = false;
          if (manualTextarea) manualTextarea.disabled = false;
          announceModel(voiceSettings.model);
        })
        .catch((error) => {
          console.error('[SiteLLM voice-avatar]', error);
          setError('Unable to load voice settings.');
          micButton.disabled = false;
          voiceArmed = false;
          updateMicButton();
          manualButton.disabled = false;
          if (manualTextarea) manualTextarea.disabled = false;
          announceModel(voiceSettings.model);
        });
    } else {
      announceModel(voiceSettings.model);
    }

    function cancelStream() {
      if (currentSource) {
        currentSource.close();
        currentSource = null;
      }
    }

    function handleResponse(question) {
      stopActiveSpeech();
      awaitingResponse = true;
      cancelStream();
      clearSourcesPanel();
      renewIdleTimer();
      const url = buildUrl(baseUrl, project, session, question, channel, voiceSettings.model, voiceSettings.reading);
      let buffer = '';
      transcript.textContent = 'Assistant is responding...';

      try {
        currentSource = new EventSource(url, { withCredentials: false });
      } catch (err) {
        setError('Your browser blocked EventSource.');
        awaitingResponse = false;
        resumeAfterResponse();
        return;
      }

      const STREAM_THRESHOLD = 120;
      const SENTENCE_END_RE = /[.!?。！？…]$/;

      function maybeSpeak(force = false) {
        if (!modeSupportsVoice) {
          spokenChars = buffer.length;
          return;
        }
        if (!('speechSynthesis' in window)) return;
        const pending = buffer.slice(spokenChars);
        const sanitizedPending = stripEmojis(pending);
        const trimmed = sanitizedPending.trim();
        if (!trimmed) {
          spokenChars = buffer.length;
          return;
        }
        const endsWithSentence = SENTENCE_END_RE.test(trimmed);
        if (!force && trimmed.length < STREAM_THRESHOLD && !endsWithSentence) {
          return;
        }
        rememberAssistantUtterance(trimmed);
        speak(sanitizedPending, lang, voiceSettings.voiceHint || voiceHint, {
          flush: false,
          rate: speechRate,
          pitch: DEFAULT_SPEECH_PITCH,
        });
        spokenChars = buffer.length;
      }

      currentSource.addEventListener('meta', (event) => {
        try {
          const meta = JSON.parse(event.data);
          if (!meta || typeof meta !== 'object') return;
          const hasReadingFlag = Object.prototype.hasOwnProperty.call(meta, 'reading_mode') || Object.prototype.hasOwnProperty.call(meta, 'reading_available');
          if (hasReadingFlag) {
            const readingActive = meta.reading_mode === true || meta.reading_available === true;
            voiceSettings.reading = readingActive;
            if (readingActive) {
              enableReadingMode();
            } else {
              disableReadingMode();
            }
          }
        } catch (err) {
          console.warn('[SiteLLM voice-avatar] meta parse error', err);
        }
      });
      currentSource.addEventListener('reading', (event) => {
        try {
          const data = JSON.parse(event.data);
          const items = Array.isArray(data?.items) ? data.items : [];
          const target = items.find((item) => Array.isArray(item?.pages) && item.pages.length) || items[0];
          if (target) {
            applyReadingData(target);
          }
        } catch (err) {
          console.warn('[SiteLLM voice-avatar] reading payload parse error', err);
        }
      });
      currentSource.addEventListener('sources', (event) => {
        try {
          const data = JSON.parse(event.data);
          const entries = Array.isArray(data?.entries) ? data.entries : [];
          updateSourcesPanel(entries);
        } catch (err) {
          console.warn('[SiteLLM voice-avatar] sources parse error', err);
        }
      });
      currentSource.addEventListener('end', () => {
        currentSource && currentSource.close();
        currentSource = null;
        const finalAnswer = stripEmojis(buffer) || 'No answer received.';
        transcript.textContent = finalAnswer;
        appendMessage('bot', buffer || 'No answer received.');
        rememberAssistantUtterance(finalAnswer);
        maybeSpeak(true);
        awaitingResponse = false;
        lastFinalUtterance = '';
        resumeAfterResponse();
      });
      currentSource.addEventListener('llm_error', () => {
        setError('Assistant failed to answer.');
        maybeSpeak(true);
        awaitingResponse = false;
        lastFinalUtterance = '';
        resumeAfterResponse();
      });
      currentSource.onerror = () => {
        setError('Connection interrupted.');
        maybeSpeak(true);
        awaitingResponse = false;
        lastFinalUtterance = '';
        resumeAfterResponse();
      };
      currentSource.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload && typeof payload.text === 'string') {
            buffer += payload.text;
            transcript.textContent = stripEmojis(buffer);
            maybeSpeak(false);
            renewIdleTimer();
          }
        } catch (err) {
          // ignore malformed chunk
        }
      };
    }

    function handleQuestion(question) {
      if (modeSupportsVoice && !voiceSettings.enabled) {
        setError('Voice assistant is disabled by the administrator.');
        return;
      }
      const trimmed = (question || '').trim();
      if (!trimmed) {
        setError('Please say or type a question.');
        resumeAfterResponse();
        return;
      }
      renewIdleTimer();
      stopActiveSpeech();
      awaitingResponse = true;
      setError('');
      appendMessage('user', `🙋 ${trimmed}`);
      handleResponse(trimmed);
    }

    micButton.addEventListener('click', () => {
      if (!modeSupportsVoice) {
        manualInput.style.display = 'block';
        setError('Microphone control is disabled in this mode. Use the text form below.');
        return;
      }
      if (!voiceSettings.enabled) {
        setError(disabledMessage);
        return;
      }
      if (!supportsSpeechRecognition()) {
        manualInput.style.display = 'block';
        setError('Speech recognition is not supported in this browser. Use the text form below.');
        return;
      }
      if (!recognition) {
        recognition = createRecognition(lang);
        recognitionBound = false;
      }
      if (!recognition) {
        manualInput.style.display = 'block';
        setError('Speech recognition is not supported in this browser. Use the text form below.');
        return;
      }
      if (voiceArmed) {
        deactivateVoice();
        return;
      }
      setError('');
      voiceArmed = true;
      updateMicButton();
      renewIdleTimer();
      beginListening();
    });

    manualButton.addEventListener('click', () => {
      if (modeSupportsVoice && !voiceSettings.enabled) {
        setError('Voice assistant is disabled by the administrator.');
        return;
      }
      const value = manualTextarea.value.trim();
      if (!value) return;
      manualTextarea.value = '';
      transcript.textContent = value;
      awaitingResponse = true;
      stopActiveSpeech();
      handleQuestion(value);
    });

    if (readingMode) {
      loadReadingPages({ reset: true });
    } else {
      renderReadingPages();
    }

    if (!recognition) {
      manualInput.style.display = 'block';
    } else {
      bindRecognitionListeners();
    }
  }

  function bootstrap() {
    const script = document.currentScript;
    if (!script) return;
    try {
      init(script);
    } catch (err) {
      console.error('[SiteLLM voice-avatar]', err);
    }
  }

  bootstrap();

  Object.assign(globalRoot, {
    version: CURRENT_VERSION,
    characters: Object.keys(CHARACTER_PRESETS),
    getCharacterPreset(key) {
      return CHARACTER_PRESETS[key] || null;
    },
    instances: instanceRegistry,
    registerInstance,
    unregisterInstance,
  });
  window.SiteLLMVoiceAvatar = globalRoot;
})();
