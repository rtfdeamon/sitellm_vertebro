const config = window.desktopConfig || {};
const widgetRoot = document.getElementById('widget-root');
const placeholder = widgetRoot.querySelector('.widget-placeholder');
const hotwordLabel = document.getElementById('hotword-label');
const hotwordToggle = document.getElementById('toggle-hotword');
const pinToggle = document.getElementById('pin-toggle');
const devtoolsBtn = document.getElementById('devtools-btn');

const HOTWORD = (config.hotword || 'Ситель, слушай').trim().toLowerCase();
const HOTWORD_LOCALE = config.hotwordLocale || 'ru-RU';
let avatarInstance = null;
let recognition = null;
let hotwordActive = true;
let readyResolve;
const widgetReady = new Promise((resolve) => {
  readyResolve = resolve;
});

function installVoiceWidget() {
  const script = document.createElement('script');
  script.defer = true;
  script.src = '../../../voice-avatar.js';
  script.dataset.baseUrl = config.baseUrl || '';
  if (config.project) script.dataset.project = config.project;
  script.dataset.mode = config.mode || 'avatar';
  script.dataset.color = config.color || '#4f7cff';
  script.dataset.readingMode = config.readingMode ? '1' : '0';
  script.dataset.voice = config.voiceHint || '';
  script.dataset.orientation = config.orientation || 'bottom-right';
  if (config.character) script.dataset.avatarCharacter = config.character;
  script.addEventListener('load', () => {
    placeholder?.remove();
    readyResolve();
  });
  widgetRoot.appendChild(script);
}

function setPinButtonState(pinned) {
  pinToggle?.setAttribute('aria-pressed', String(Boolean(pinned)));
  pinToggle.textContent = pinned ? '📌' : '📍';
  pinToggle.title = pinned ? 'Открепить от верхнего слоя' : 'Закрепить поверх других окон';
}

async function updatePinState() {
  if (!window.desktopAPI || !pinToggle) return;
  try {
    const pinned = await window.desktopAPI.isPinned();
    setPinButtonState(pinned);
  } catch (error) {
    console.error('[SiteLLM desktop] Failed to read pin state', error);
  }
}

function getVoiceInstance() {
  if (avatarInstance) return avatarInstance;
  const pool = window.SiteLLMVoiceAvatar && window.SiteLLMVoiceAvatar.instances;
  if (pool && pool.length) {
    avatarInstance = pool[pool.length - 1];
  }
  return avatarInstance;
}

function activateVoiceCapture() {
  const instance = getVoiceInstance();
  if (!instance) return false;
  if (typeof instance.startVoiceCapture === 'function') {
    return instance.startVoiceCapture();
  }
  const mic = instance.element?.querySelector?.('.sitellm-voice-mic');
  if (mic) {
    mic.click();
    return true;
  }
  return false;
}

function autoEnableReadingMode(instance) {
  if (!instance || !config.readingMode) return;
  if (typeof instance.enableReadingMode === 'function') {
    instance.enableReadingMode();
  }
}

function startHotwordRecognition() {
  if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
    hotwordActive = false;
    if (hotwordToggle) {
      hotwordToggle.disabled = true;
      hotwordToggle.textContent = 'Горячее слово недоступно';
    }
    return;
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = HOTWORD_LOCALE;
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.addEventListener('result', (event) => {
    if (!hotwordActive) return;
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (!result.isFinal) continue;
      const transcript = result[0]?.transcript?.trim().toLowerCase();
      if (!transcript) continue;
      if (transcript.includes(HOTWORD)) {
        activateVoiceCapture();
      }
    }
  });

  recognition.addEventListener('end', () => {
    if (hotwordActive) {
      try {
        recognition.start();
      } catch (error) {
        console.warn('[SiteLLM desktop] Hotword restart failed', error);
      }
    }
  });

  recognition.addEventListener('error', (event) => {
    console.warn('[SiteLLM desktop] Hotword recognition error', event.error);
  });

  try {
    recognition.start();
  } catch (error) {
    console.error('[SiteLLM desktop] Failed to start hotword recognition', error);
    hotwordActive = false;
    if (hotwordToggle) {
      hotwordToggle.disabled = true;
      hotwordToggle.textContent = 'Прослушивание отключено';
    }
  }
}

function stopHotwordRecognition() {
  if (recognition) {
    try {
      recognition.stop();
    } catch (error) {
      console.warn('[SiteLLM desktop] stop() failed', error);
    }
  }
}

function bindUI() {
  if (hotwordLabel) {
    hotwordLabel.textContent = HOTWORD || '—';
  }

  if (hotwordToggle) {
    hotwordToggle.setAttribute('aria-pressed', 'true');
    hotwordToggle.addEventListener('click', () => {
      hotwordActive = !hotwordActive;
      hotwordToggle.setAttribute('aria-pressed', String(hotwordActive));
      hotwordToggle.textContent = hotwordActive ? 'Отключить прослушивание' : 'Включить прослушивание';
      if (hotwordActive) {
        try {
          recognition?.start();
        } catch (error) {
          console.warn('[SiteLLM desktop] restart hotword failed', error);
        }
      } else {
        stopHotwordRecognition();
      }
    });
  }

  if (pinToggle && window.desktopAPI) {
    pinToggle.addEventListener('click', async () => {
      try {
        const pinned = await window.desktopAPI.togglePin();
        setPinButtonState(pinned);
      } catch (error) {
        console.error('[SiteLLM desktop] toggle pin failed', error);
      }
    });
    updatePinState();
  }

  if (devtoolsBtn && window.desktopAPI) {
    devtoolsBtn.addEventListener('click', () => {
      window.desktopAPI.openDevTools();
    });
  }
}

function handleInstanceReady(instance) {
  avatarInstance = instance;
  autoEnableReadingMode(instance);
}

document.addEventListener('sitellm-voice-avatar-ready', (event) => {
  handleInstanceReady(event.detail);
});

installVoiceWidget();
bindUI();
startHotwordRecognition();

widgetReady.then(() => {
  const current = getVoiceInstance();
  if (current) {
    handleInstanceReady(current);
  }
});

window.addEventListener('beforeunload', () => {
  stopHotwordRecognition();
});

window.SiteLLMDesktop = {
  get config() {
    return config;
  },
  get hotwordActive() {
    return hotwordActive;
  },
  toggleHotword(value) {
    const target = typeof value === 'boolean' ? value : !hotwordActive;
    if (hotwordToggle) {
      hotwordToggle.click();
    } else {
      hotwordActive = target;
      if (hotwordActive) {
        startHotwordRecognition();
      } else {
        stopHotwordRecognition();
      }
    }
    return hotwordActive;
  }
};
