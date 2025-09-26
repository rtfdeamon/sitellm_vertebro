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
    .sitellm-voice-avatar-label {
      position: relative;
      z-index: 3;
      font-size: 18px;
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

  const DEFAULT_SPEECH_RATE = 1.2;
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
    if (normalizedHint) {
      const direct = list.find((voice) => voice.name.toLowerCase() === normalizedHint);
      if (direct) return direct;
    }
    const pleasantCandidates = ['milena', 'alena', 'vera', 'siri', 'anna', 'natasha', 'victoria', 'vera (enhanced)'];
    if (!normalizedHint) {
      const pleasant = list.find((voice) => pleasantCandidates.includes(voice.name.toLowerCase()));
      if (pleasant) return pleasant;
    }
    const langLower = (lang || '').trim().toLowerCase();
    if (langLower) {
      let fullMatch = list.find((voice) => (voice.lang || '').toLowerCase() === langLower);
      if (fullMatch) return fullMatch;
      const prefix = langLower.split('-')[0];
      const prefixMatch = list.find((voice) => (voice.lang || '').toLowerCase().startsWith(prefix));
      if (prefixMatch) return prefixMatch;
    }
    const pleasantFallback = list.find((voice) => pleasantCandidates.includes(voice.name.toLowerCase()));
    return pleasantFallback || list[0] || null;
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
    const readingMode = script.dataset.readingMode === '1';
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
    header.appendChild(avatar);

    const status = document.createElement('div');
    status.className = 'sitellm-voice-status';
    status.innerHTML = '<span class="bot">💬 Ready when you are</span>';
    if (readingMode) {
      const hint = document.createElement('span');
      hint.className = 'bot';
      hint.textContent = '📖 Reading mode enabled. Ask for the next page when you are ready.';
      status.appendChild(hint);
    }

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

    const content = document.createElement('div');
    content.className = 'sitellm-voice-content';
    content.appendChild(status);
    content.appendChild(actions);
    content.appendChild(manualInput);
    content.appendChild(errorBox);

    container.appendChild(header);
    container.appendChild(content);

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
      voiceHint,
      reading: readingMode,
    };
    let spokenChars = 0;

    const IDLE_TIMEOUT_MS = 90000;
    let voiceArmed = false;
    let listening = false;
    let idleTimer = null;
    let recognitionBound = false;
    let currentUtterance = null;
    let awaitingResponse = false;
    let lastFinalUtterance = '';

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
      stopMicMonitor();
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
      if (message) setError(message); else setError('');
      transcript.textContent = 'Tap the microphone and ask your question.';
    }

    function resumeAfterResponse() {
      renewIdleTimer();
    }

    function resetSpeechStream() {
      spokenChars = 0;
      if ('speechSynthesis' in window) {
        try { speechSynthesis.cancel(); } catch (_) {}
      }
      currentUtterance = null;
    }

    function stopActiveSpeech() {
      if (!('speechSynthesis' in window)) return;
      currentUtterance = null;
      awaitingResponse = false;
      stopVoiceVisualizer();
      try {
        speechSynthesis.cancel();
      } catch (_) {}
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
      if (!voiceVisual) return;
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
    }

    function speak(text, lang, voiceHint, options = {}) {
      if (!('speechSynthesis' in window)) return;
      const {
        flush = true,
        rate = DEFAULT_SPEECH_RATE,
        pitch = DEFAULT_SPEECH_PITCH,
        voiceOverride,
      } = options;
      const sanitized = stripEmojis(text);
      if (!sanitized.trim()) return;
      const utterance = new SpeechSynthesisUtterance(sanitized);
      if (lang) utterance.lang = lang;
      utterance.rate = rate;
      utterance.pitch = pitch;
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
      utterance.onend = () => {
        currentUtterance = null;
        awaitingResponse = false;
        stopVoiceVisualizer();
        renewIdleTimer();
      };
      utterance.onerror = () => {
        currentUtterance = null;
        stopVoiceVisualizer();
      };
      speechSynthesis.speak(utterance);
    }

    function applyMicLevel(level) {
      if (!micVisual) return;
      micVisual.classList.add('active');
      micVisual.style.transform = `scale(${1 + Math.min(0.6, level * 0.6)})`;
      micVisual.style.opacity = `${Math.min(0.95, 0.25 + level * 1.3)}`;
    }

    async function startMicMonitor() {
      if (!micVisual || !navigator.mediaDevices?.getUserMedia || micMonitor.failed) return;
      try {
        if (!micMonitor.stream) {
          micMonitor.stream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: false,
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
      stopActiveSpeech();
      awaitingResponse = true;
      cancelStream();
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
        speak(sanitizedPending, lang, voiceSettings.voiceHint || voiceHint, {
          flush: false,
          rate: DEFAULT_SPEECH_RATE,
          pitch: DEFAULT_SPEECH_PITCH,
        });
        spokenChars = buffer.length;
      }

      currentSource.addEventListener('meta', () => {
        // optional meta
      });
      currentSource.addEventListener('end', () => {
        currentSource && currentSource.close();
        currentSource = null;
        transcript.textContent = stripEmojis(buffer) || 'No answer received.';
        appendMessage('bot', buffer || 'No answer received.');
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
      stopActiveSpeech();
      awaitingResponse = true;
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
      awaitingResponse = true;
      stopActiveSpeech();
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
