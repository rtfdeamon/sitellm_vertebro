(() => {
  const CURRENT_VERSION = '1.0.0';
  const STYLE_ID = '__sitellmVoiceAvatarStyles';
  const projectConfigCache = new Map();

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
    @keyframes sitellmWave {
      0% { transform: scale(0.95); opacity: 0.4; }
      70% { transform: scale(1.15); opacity: 0.05; }
      100% { transform: scale(0.95); opacity: 0.0; }
    }
    .sitellm-voice-widget {
      position: relative;
      width: min(360px, 100%);
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
      width: 82px;
      height: 82px;
      border-radius: 50%;
      background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.7), rgba(${accent}, 0.9));
      display: grid;
      place-items: center;
      font-weight: 700;
      color: #fff;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      animation: sitellmAvatarFloat 4.5s ease-in-out infinite;
      overflow: hidden;
    }
    .sitellm-voice-avatar::after,
    .sitellm-voice-avatar::before {
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 50%;
      border: 2px solid rgba(${accent}, 0.45);
      animation: sitellmWave 3.6s linear infinite;
    }
    .sitellm-voice-avatar::after {
      animation-delay: 1.5s;
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
    instance.interimResults = false;
    instance.maxAlternatives = 1;
    return instance;
  }

  function buildUrl(base, project, session, question, channel, model) {
    const params = new URLSearchParams({ question, session_id: session, channel });
    if (project) params.set('project', project);
    if (model) params.set('model', model);
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

  function speak(text, lang, voiceHint, options = {}) {
    if (!('speechSynthesis' in window)) return;
    const { flush = true } = options;
    const sanitized = stripEmojis(text);
    if (!sanitized.trim()) return;
    const utterance = new SpeechSynthesisUtterance(sanitized);
    if (lang) utterance.lang = lang;
    if (voiceHint) {
      const voices = speechSynthesis.getVoices();
      const match = voices.find((voice) => voice.name === voiceHint || voice.lang === voiceHint);
      if (match) utterance.voice = match;
    }
    if (flush) {
      try {
        speechSynthesis.cancel();
      } catch (_) {}
    }
    speechSynthesis.speak(utterance);
  }

  function init(script) {
    const baseUrl = resolveBaseUrl(script);
    const project = script.dataset.project || '';
    const accentRgb = hexToRgb(script.dataset.color || '#4f7cff');
    const avatarLabel = script.dataset.label || 'AI';
    const lang = script.dataset.lang || 'ru-RU';
    const voiceHint = script.dataset.voice || '';
    const datasetVoiceModel = script.dataset.voiceModel || '';
    const headline = script.dataset.headline || 'AI Consultant';
    const subheadline = script.dataset.subtitle || 'Talk to me using your voice';

    ensureStyles(accentRgb);

    const container = document.createElement('section');
    container.className = 'sitellm-voice-widget';

    const header = document.createElement('div');
    header.className = 'sitellm-voice-header';
    header.innerHTML = `<div><strong>${headline}</strong><div>${subheadline}</div></div>`;

    const avatar = document.createElement('div');
    avatar.className = 'sitellm-voice-avatar';
    avatar.textContent = avatarLabel;
    header.appendChild(avatar);

    const status = document.createElement('div');
    status.className = 'sitellm-voice-status';
    status.innerHTML = '<span class="bot">💬 Ready when you are</span>';

    const errorBox = document.createElement('div');
    errorBox.className = 'sitellm-voice-error';

    const actions = document.createElement('div');
    actions.className = 'sitellm-voice-actions';

    const micButton = document.createElement('button');
    micButton.className = 'sitellm-voice-mic';
    micButton.type = 'button';
    micButton.innerHTML = '🎤';

    const transcript = document.createElement('div');
    transcript.className = 'sitellm-voice-transcript';
    transcript.textContent = 'Tap the microphone and ask your question.';

    actions.appendChild(micButton);
    actions.appendChild(transcript);

    const manualInput = document.createElement('div');
    manualInput.className = 'sitellm-voice-input';
    manualInput.innerHTML = `
      <textarea placeholder="Type your question if voice input is unavailable..."></textarea>
      <button type="button">Send</button>
    `;

    container.appendChild(header);
    container.appendChild(status);
    container.appendChild(actions);
    container.appendChild(manualInput);
    container.appendChild(errorBox);

    script.insertAdjacentElement('beforebegin', container);

    const manualTextarea = manualInput.querySelector('textarea');
    const manualButton = manualInput.querySelector('button');

    const session = sessionKey(project);
    const channel = 'voice-avatar';

    let recognition = supportsSpeechRecognition() ? createRecognition(lang) : null;
    let currentSource = null;
    const voiceSettings = {
      enabled: true,
      model: datasetVoiceModel,
    };
    let spokenChars = 0;

    const IDLE_TIMEOUT_MS = 90000;
    let voiceArmed = false;
    let listening = false;
    let restartOnEnd = false;
    let awaitingResume = false;
    let idleTimer = null;
    let recognitionBound = false;

    function clearIdleTimer() {
      if (idleTimer) {
        clearTimeout(idleTimer);
        idleTimer = null;
      }
    }

    function updateMicButton() {
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
      if (!voiceArmed) return;
      idleTimer = window.setTimeout(() => {
        if (!voiceArmed) return;
        deactivateVoice('Voice assistant paused due to inactivity.');
        appendMessage('bot', '💤 Voice assistant paused due to inactivity');
      }, IDLE_TIMEOUT_MS);
    }

    function stopRecognitionInternal() {
      listening = false;
      updateMicButton();
      if (recognition) {
        try {
          recognition.stop();
        } catch (_) {}
      }
    }

    function bindRecognitionListeners() {
      if (!recognition || recognitionBound) return;
      recognitionBound = true;

      recognition.addEventListener('result', (event) => {
        renewIdleTimer();
        if (!event.results || !event.results[0]) {
          setError('Speech recognition did not return any result.');
          resumeAfterResponse();
          return;
        }
        const transcriptText = (event.results[0][0]?.transcript || '').trim();
        if (!transcriptText) {
          resumeAfterResponse();
          return;
        }
        transcript.textContent = transcriptText;
        if (voiceArmed) {
          pauseForResponse();
        }
        handleQuestion(transcriptText);
      });

      recognition.addEventListener('error', (event) => {
        const message = `Voice input error: ${event.error || 'unknown'}`;
        setError(message);
        listening = false;
        restartOnEnd = false;
        updateMicButton();
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          deactivateVoice('Microphone access is blocked. Use the text form below.');
          manualInput.style.display = 'block';
          return;
        }
        if (voiceArmed && !awaitingResume) {
          setTimeout(() => {
            if (voiceArmed && !listening && !awaitingResume) {
              beginListening();
            }
          }, 1000);
        }
      });

      recognition.addEventListener('end', () => {
        const shouldRestart = restartOnEnd && voiceArmed && !awaitingResume;
        listening = false;
        restartOnEnd = false;
        updateMicButton();
        if (shouldRestart) {
          setTimeout(() => {
            if (voiceArmed && !listening && !awaitingResume) {
              beginListening();
            }
          }, 300);
        }
      });
    }

    function beginListening() {
      if (!recognition) return;
      bindRecognitionListeners();
      listening = true;
      awaitingResume = false;
      restartOnEnd = true;
      updateMicButton();
      transcript.textContent = 'Listening...';
      renewIdleTimer();
      try {
        recognition.start();
      } catch (err) {
        restartOnEnd = false;
        listening = false;
        updateMicButton();
        if (err && err.name === 'InvalidStateError') {
          setTimeout(() => {
            if (voiceArmed && !listening && !awaitingResume) {
              beginListening();
            }
          }, 400);
        } else {
          setError('Unable to access microphone.');
          deactivateVoice();
          manualInput.style.display = 'block';
        }
      }
    }

    function deactivateVoice(message) {
      voiceArmed = false;
      awaitingResume = false;
      restartOnEnd = false;
      clearIdleTimer();
      cancelStream();
      stopRecognitionInternal();
      if (message) setError(message); else setError('');
      transcript.textContent = 'Tap the microphone and ask your question.';
    }

    function pauseForResponse() {
      awaitingResume = true;
      restartOnEnd = false;
      stopRecognitionInternal();
      transcript.textContent = 'Processing your request...';
    }

    function resumeWhenReady() {
      if (!voiceArmed || listening) return;
      if ('speechSynthesis' in window && (speechSynthesis.speaking || speechSynthesis.pending)) {
        setTimeout(resumeWhenReady, 400);
        return;
      }
      beginListening();
    }

    function resumeAfterResponse() {
      if (!voiceArmed) return;
      awaitingResume = false;
      renewIdleTimer();
      resumeWhenReady();
    }

    function resetSpeechStream() {
      spokenChars = 0;
      if ('speechSynthesis' in window) {
        try { speechSynthesis.cancel(); } catch (_) {}
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

    const disabledMessage = 'Voice assistant is disabled by the administrator.';
    let modelAnnounced = false;

    function announceModel(model) {
      if (!model || modelAnnounced) return;
      appendMessage('bot', `⚙️ Model: ${model}`);
      modelAnnounced = true;
    }

    const normalizedBase = baseUrl.replace(/\/$/, '');
    if (project) {
      micButton.disabled = true;
      manualButton.disabled = true;
      if (manualTextarea) manualTextarea.disabled = true;
      fetchProjectConfig(normalizedBase, project)
        .then((cfg) => {
          voiceSettings.enabled = cfg.enabled;
          if (cfg.model) {
            voiceSettings.model = cfg.model;
          }
          if (!voiceSettings.enabled) {
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
      cancelStream();
      renewIdleTimer();
      const url = buildUrl(baseUrl, project, session, question, channel, voiceSettings.model);
      let buffer = '';
      resetSpeechStream();
      transcript.textContent = 'Assistant is responding...';

      try {
        currentSource = new EventSource(url, { withCredentials: false });
      } catch (err) {
        setError('Your browser blocked EventSource.');
        resumeAfterResponse();
        return;
      }

      const STREAM_THRESHOLD = 120;
      const SENTENCE_END_RE = /[.!?。！？…]$/;

      function maybeSpeak(force = false) {
        if (!('speechSynthesis' in window)) return;
        const pending = buffer.slice(spokenChars);
        const trimmed = pending.trim();
        if (!trimmed) return;
        const endsWithSentence = SENTENCE_END_RE.test(trimmed);
        if (!force && trimmed.length < STREAM_THRESHOLD && !endsWithSentence) {
          return;
        }
        speak(pending, lang, voiceHint, { flush: false });
        spokenChars = buffer.length;
      }

      currentSource.addEventListener('meta', () => {
        // optional meta
      });
      currentSource.addEventListener('end', () => {
        currentSource && currentSource.close();
        currentSource = null;
        transcript.textContent = buffer || 'No answer received.';
        appendMessage('bot', buffer || 'No answer received.');
        maybeSpeak(true);
        resumeAfterResponse();
      });
      currentSource.addEventListener('llm_error', () => {
        setError('Assistant failed to answer.');
        maybeSpeak(true);
        resumeAfterResponse();
      });
      currentSource.onerror = () => {
        setError('Connection interrupted.');
        maybeSpeak(true);
        resumeAfterResponse();
      };
      currentSource.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload && typeof payload.text === 'string') {
            buffer += payload.text;
            transcript.textContent = buffer;
            maybeSpeak(false);
            renewIdleTimer();
          }
        } catch (err) {
          // ignore malformed chunk
        }
      };
    }

    function handleQuestion(question) {
      if (!voiceSettings.enabled) {
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
      if (voiceArmed && !awaitingResume) {
        pauseForResponse();
      }
      resetSpeechStream();
      setError('');
      appendMessage('user', `🙋 ${trimmed}`);
      handleResponse(trimmed);
    }

    micButton.addEventListener('click', () => {
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
      if (!voiceSettings.enabled) {
        setError('Voice assistant is disabled by the administrator.');
        return;
      }
      const value = manualTextarea.value.trim();
      if (!value) return;
      manualTextarea.value = '';
      transcript.textContent = value;
      if (voiceArmed) {
        pauseForResponse();
      }
      handleQuestion(value);
    });

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

  window.SiteLLMVoiceAvatar = {
    version: CURRENT_VERSION,
  };
})();
