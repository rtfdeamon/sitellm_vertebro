(function (global) {
  const doc = global.document;
  const UI = global.UIUtils || {};
  const formatBytesOptionalFn = UI.formatBytesOptional || ((value) => {
    const numeric = Number(value || 0);
    if (!Number.isFinite(numeric) || numeric <= 0) return '—';
    if (typeof UI.formatBytes === 'function') {
      return UI.formatBytes(numeric);
    }
    return `${numeric} B`;
  });

  const translate = (key, fallback = '', params = null) => {
    try {
      if (typeof global.t === 'function') {
        const result = params ? global.t(key, params) : global.t(key);
        if (result && result !== key) return result;
      }
    } catch (error) {
      console.warn('voice_translate_failed', error);
    }
    if (fallback && params && typeof fallback === 'string') {
      return fallback.replace(/\{(\w+)\}/g, (_, token) =>
        Object.prototype.hasOwnProperty.call(params, token) ? String(params[token]) : '',
      );
    }
    return fallback || key;
  };

  const elements = {
    card: doc.getElementById('voiceTrainingCard'),
    fileInput: doc.getElementById('voiceSampleInput'),
    uploadBtn: doc.getElementById('voiceSampleUpload'),
    uploadStatus: doc.getElementById('voiceUploadStatus'),
    summary: doc.getElementById('voiceTrainingSummary'),
    samplesContainer: doc.getElementById('voiceSamplesContainer'),
    samplesEmpty: doc.getElementById('voiceSamplesEmpty'),
    trainButton: doc.getElementById('voiceTrainButton'),
    trainStatus: doc.getElementById('voiceTrainStatus'),
    recordButton: doc.getElementById('voiceRecordBtn'),
    recordStatus: doc.getElementById('voiceRecordStatus'),
    jobsContainer: doc.getElementById('voiceJobsContainer'),
    fileLabel: doc.getElementById('voiceSampleLabel'),
  };

  const hasUi = Object.values(elements).some(Boolean);
  const noopAsync = async () => {};
  const noop = () => {};

  if (!hasUi) {
    global.VoiceModule = {
      refresh: noopAsync,
      reset: noop,
      handleLanguageApplied: noop,
    };
    return;
  }

  const VOICE_ACTIVE_STATUSES = new Set(['queued', 'preparing', 'training', 'validating']);
  const VOICE_MIN_SAMPLE_COUNT = 3;
  const MEDIA_RECORDER_SUPPORTED = !!(global.navigator?.mediaDevices?.getUserMedia && global.MediaRecorder);
  const MAX_RECORDING_MS = 60_000;

  const state = {
    samples: [],
    jobs: [],
    pollTimer: null,
    jobPending: false,
    recorder: {
      stream: null,
      instance: null,
      chunks: [],
      timer: null,
      startedAt: 0,
      active: false,
      uploading: false,
      skipUpload: false,
    },
  };

  const setRecordStatus = (message) => {
    if (elements.recordStatus) elements.recordStatus.textContent = message;
  };

  const translateRecordLabel = (recording) => (
    recording
      ? translate('voiceStopRecording', 'Stop recording')
      : translate('voiceRecordButton', 'Record sample')
  );

  const updateFileSelectionLabel = () => {
    if (!elements.fileLabel) return;
    const files = elements.fileInput?.files;
    if (!files || !files.length) {
      elements.fileLabel.dataset.i18n = 'fileNoFileSelected';
      elements.fileLabel.textContent = translate('fileNoFileSelected', 'No files selected');
      return;
    }
    if (files.length === 1) {
      delete elements.fileLabel.dataset.i18n;
      elements.fileLabel.textContent = files[0].name;
      return;
    }
    elements.fileLabel.dataset.i18n = 'fileFilesSelected';
    elements.fileLabel.textContent = translate('fileFilesSelected', '{count} files selected', { count: files.length });
  };

  const refreshVoiceTrainingState = () => {
    const currentProject = (global.currentProject || '').trim();
    const activeJob = state.jobPending || state.jobs.some((job) => VOICE_ACTIVE_STATUSES.has(String(job.status || '').toLowerCase()));
    const enoughSamples = state.samples.length >= VOICE_MIN_SAMPLE_COUNT;

    if (elements.uploadBtn) {
      elements.uploadBtn.disabled = !currentProject || activeJob || state.recorder.active || state.recorder.uploading;
    }
    if (elements.fileInput) {
      elements.fileInput.disabled = !currentProject || state.recorder.active;
      if (!currentProject) {
        updateFileSelectionLabel();
      }
    }
    if (elements.recordButton) {
      elements.recordButton.disabled = !MEDIA_RECORDER_SUPPORTED || !currentProject || activeJob || state.recorder.uploading;
      elements.recordButton.textContent = translateRecordLabel(state.recorder.active);
    }
    if (elements.trainButton) {
      elements.trainButton.disabled = !currentProject || activeJob || !enoughSamples;
    }
    if (elements.trainStatus) {
      if (activeJob) {
        elements.trainStatus.textContent = translate('voiceTrainingAlreadyRunning', 'Training is already running');
      } else if (!enoughSamples && state.samples.length > 0) {
        elements.trainStatus.textContent = translate('voiceAddMoreSamples', 'Add more samples');
      } else if ([translate('voiceTrainingAlreadyRunning', 'Training is already running'), translate('voiceAddMoreSamples', 'Add more samples')].includes(elements.trainStatus.textContent)) {
        elements.trainStatus.textContent = '—';
      }
    }
    updateFileSelectionLabel();
  };

  const cleanupRecorderStream = () => {
    const stream = state.recorder.stream;
    if (!stream) return;
    try {
      stream.getTracks().forEach((track) => track.stop());
    } catch (error) {
      console.warn('voice_record_stream_cleanup_failed', error);
    }
    state.recorder.stream = null;
  };

  const stopVoiceRecording = (skipUpload = false) => {
    if (!MEDIA_RECORDER_SUPPORTED) return;
    if (state.recorder.timer) {
      clearInterval(state.recorder.timer);
      state.recorder.timer = null;
    }
    state.recorder.skipUpload = skipUpload;
    const recorder = state.recorder.instance;
    if (!recorder) return;
    try {
      recorder.stop();
    } catch (error) {
      console.warn('voice_record_stop_failed', error);
    }
  };

  const resetVoiceTrainingUi = (message) => {
    if (elements.uploadStatus) elements.uploadStatus.textContent = '—';
    if (elements.trainStatus) elements.trainStatus.textContent = '—';
    if (elements.summary) {
      elements.summary.textContent = message || translate('voiceMinSamplesRequired', 'Upload at least 3 samples.');
    }
    stopVoiceRecording(true);
    cleanupRecorderStream();
    state.recorder.uploading = false;
    state.samples = [];
    state.jobs = [];
    if (elements.recordStatus) elements.recordStatus.textContent = '—';
    if (elements.samplesContainer) {
      elements.samplesContainer.innerHTML = '';
      if (elements.samplesEmpty) {
        elements.samplesEmpty.textContent = translate('voiceSamplesEmpty', 'No samples uploaded.');
        elements.samplesContainer.appendChild(elements.samplesEmpty);
      }
    }
    if (elements.jobsContainer) {
      elements.jobsContainer.innerHTML = '';
    }
    refreshVoiceTrainingState();
    updateFileSelectionLabel();
  };

  const uploadRecordedBlob = async (blob, filename) => {
    const project = (global.currentProject || '').trim();
    if (!project) {
      setRecordStatus(translate('voiceSelectProjectToAddSample', 'Select a project to add a recording.'));
      return;
    }
    state.recorder.uploading = true;
    refreshVoiceTrainingState();
    setRecordStatus(translate('voiceUploadRecording', 'Uploading recording…'));
    try {
      const formData = new FormData();
      formData.append('project', project);
      formData.append('files', new File([blob], filename, { type: blob.type || 'audio/webm' }));
      const response = await fetch('/api/v1/voice/samples', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      renderVoiceSamples(data.samples || []);
      setRecordStatus(translate('voiceRecordingUploaded', 'Recording uploaded'));
      setTimeout(() => {
        if (!state.recorder.active) setRecordStatus('—');
      }, 4000);
    } catch (error) {
      console.error('voice_record_upload_failed', error);
      setRecordStatus(translate('voiceRecordingLoadError', 'Failed to load recording.'));
    } finally {
      state.recorder.uploading = false;
      refreshVoiceTrainingState();
    }
  };

  const handleRecorderStop = () => {
    state.recorder.active = false;
    if (elements.recordButton) {
      elements.recordButton.textContent = translateRecordLabel(false);
    }
    if (state.recorder.timer) {
      clearInterval(state.recorder.timer);
      state.recorder.timer = null;
    }
    cleanupRecorderStream();
    const recorder = state.recorder.instance;
    state.recorder.instance = null;
    const chunks = state.recorder.chunks.splice(0, state.recorder.chunks.length);
    if (state.recorder.skipUpload || !chunks.length) {
      setRecordStatus('—');
      state.recorder.skipUpload = false;
      refreshVoiceTrainingState();
      return;
    }
    const mime = recorder?.mimeType || 'audio/webm';
    const blob = new Blob(chunks, { type: mime });
    const ext = mime.includes('mp4') ? 'm4a' : mime.includes('mpeg') ? 'mp3' : 'webm';
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `recording-${timestamp}.${ext}`;
    uploadRecordedBlob(blob, filename);
    refreshVoiceTrainingState();
  };

  const startVoiceRecording = async () => {
    if (!MEDIA_RECORDER_SUPPORTED) return;
    const project = (global.currentProject || '').trim();
    if (!project) {
      setRecordStatus(translate('voiceSelectProjectForRecording', 'Select a project to record.'));
      return;
    }
    if (state.recorder.uploading) {
      setRecordStatus(translate('voiceUploadPending', 'Please wait until the upload finishes.'));
      return;
    }
    setRecordStatus(translate('voiceMicPreparing', 'Preparing microphone…'));
    try {
      if (!state.recorder.stream) {
        state.recorder.stream = await global.navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: { ideal: true },
            noiseSuppression: { ideal: true },
            channelCount: { ideal: 1 },
            sampleRate: { ideal: 44100 },
          },
        });
      }
    } catch (error) {
      console.error('voice_record_permission_failed', error);
      setRecordStatus(translate('voiceMicDenied', 'Microphone access denied.'));
      cleanupRecorderStream();
      return;
    }

    const mimeCandidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/mpeg',
    ];
    let options = {};
    const supported = mimeCandidates.find((type) => {
      try {
        return global.MediaRecorder.isTypeSupported(type);
      } catch {
        return false;
      }
    });
    if (supported) options = { mimeType: supported };

    try {
      state.recorder.instance = new global.MediaRecorder(state.recorder.stream, options);
    } catch (error) {
      console.error('voice_record_init_failed', error);
      setRecordStatus(translate('voiceRecordingStartError', 'Failed to start recording.'));
      cleanupRecorderStream();
      return;
    }

    state.recorder.chunks = [];
    state.recorder.skipUpload = false;
    state.recorder.instance.addEventListener('dataavailable', (event) => {
      if (event.data && event.data.size > 0) {
        state.recorder.chunks.push(event.data);
      }
    });
    state.recorder.instance.addEventListener('stop', handleRecorderStop);
    state.recorder.instance.addEventListener('error', (event) => {
      console.error('voice_record_error', event.error);
      setRecordStatus(translate('voiceRecordingError', 'Recording error.'));
      cleanupRecorderStream();
    });
    state.recorder.instance.start(1000);
    state.recorder.active = true;
    state.recorder.startedAt = Date.now();
    if (elements.recordButton) {
      elements.recordButton.textContent = translateRecordLabel(true);
    }
    state.recorder.timer = global.setInterval(() => {
      const elapsed = Date.now() - state.recorder.startedAt;
      setRecordStatus(
        translate('voiceRecordingSeconds', 'Recording {seconds} s', {
          seconds: Math.floor(elapsed / 1000),
        }),
      );
      if (elapsed >= MAX_RECORDING_MS) {
        stopVoiceRecording();
      }
    }, 1000);
    refreshVoiceTrainingState();
  };

  const renderVoiceSamples = (samples) => {
    state.samples = Array.isArray(samples) ? samples : [];
    if (!elements.samplesContainer) return;
    elements.samplesContainer.innerHTML = '';
    const total = state.samples.length;
    const remaining = Math.max(0, VOICE_MIN_SAMPLE_COUNT - total);
  if (elements.summary) {
    elements.summary.textContent = remaining > 0
      ? translate('voiceMinSamplesRemaining', 'Upload at least {min} samples. Remaining: {remaining}.', {
          min: VOICE_MIN_SAMPLE_COUNT,
          remaining,
        })
      : translate('voiceSamplesReady', 'Enough samples collected. You can start training.');
  }
    if (!total) {
      if (elements.samplesEmpty) {
        elements.samplesEmpty.textContent = translate('voiceSamplesEmpty', 'No samples uploaded.');
        elements.samplesContainer.appendChild(elements.samplesEmpty);
      }
      refreshVoiceTrainingState();
      return;
    }
    const list = doc.createElement('div');
    list.className = 'voice-samples-list';
    state.samples.forEach((sample) => {
      const row = doc.createElement('div');
      row.className = 'voice-sample-row';
      const label = doc.createElement('div');
      label.style.display = 'flex';
      label.style.flexDirection = 'column';
      label.style.gap = '2px';
      label.innerHTML = `<strong>${sample.filename}</strong><span class="muted">${formatBytesOptionalFn(sample.sizeBytes || 0)}</span>`;
      const removeBtn = doc.createElement('button');
      removeBtn.type = 'button';
      removeBtn.textContent = translate('voiceDeleteSample', 'Delete');
      removeBtn.addEventListener('click', () => deleteVoiceSample(sample.id));
      row.appendChild(label);
      row.appendChild(removeBtn);
      list.appendChild(row);
    });
    elements.samplesContainer.appendChild(list);
    refreshVoiceTrainingState();
  };

  const renderVoiceJobs = (jobs) => {
    state.jobs = Array.isArray(jobs) ? jobs : [];
    if (!elements.jobsContainer) return;
    elements.jobsContainer.innerHTML = '';
    if (!state.jobs.length) {
      const placeholder = doc.createElement('div');
      placeholder.className = 'muted';
      placeholder.dataset.i18n = 'voiceHistoryEmpty';
      placeholder.textContent = translate('voiceHistoryEmpty', 'Training history will appear after the first run.');
      elements.jobsContainer.appendChild(placeholder);
      refreshVoiceTrainingState();
      return;
    }
    state.jobs.forEach((job) => {
      const row = doc.createElement('div');
      row.className = 'voice-job-entry';
      const statusLabel = doc.createElement('div');
      const progressPct = job.progress != null ? Math.round(Math.max(0, Math.min(1, job.progress)) * 100) : 0;
      statusLabel.textContent = `${job.status} · ${progressPct}%`;
      if (job.message) {
        const hint = doc.createElement('div');
        hint.className = 'muted';
        hint.textContent = job.message;
        statusLabel.appendChild(doc.createElement('br'));
        statusLabel.appendChild(hint);
      }
      const progressContainer = doc.createElement('div');
      progressContainer.className = 'voice-progress-bar';
      const progressFill = doc.createElement('div');
      progressFill.className = 'voice-progress-fill';
      progressFill.style.width = `${progressPct}%`;
      progressContainer.appendChild(progressFill);
      row.appendChild(statusLabel);
      row.appendChild(progressContainer);
      elements.jobsContainer.appendChild(row);
    });
    refreshVoiceTrainingState();
  };

  const clearJobsPoll = () => {
    if (state.pollTimer) {
      clearTimeout(state.pollTimer);
      state.pollTimer = null;
    }
  };

  const refreshVoiceTraining = async (projectName) => {
    clearJobsPoll();
    if (!projectName) {
      resetVoiceTrainingUi(translate('voiceSelectProjectToUpload', 'Select a project to upload samples.'));
      return;
    }
    if (elements.uploadBtn) elements.uploadBtn.disabled = false;
    if (elements.fileInput) elements.fileInput.disabled = false;
    try {
      const [samplesRes, jobsRes] = await Promise.all([
        fetch(`/api/v1/voice/samples?project=${encodeURIComponent(projectName)}`, { credentials: 'same-origin' }),
        fetch(`/api/v1/voice/jobs?project=${encodeURIComponent(projectName)}&limit=5`, { credentials: 'same-origin' }),
      ]);
      if (!samplesRes.ok) throw new Error('samples_fetch_failed');
      if (!jobsRes.ok) throw new Error('jobs_fetch_failed');
      const samplesData = await samplesRes.json();
      const jobsData = await jobsRes.json();
      renderVoiceSamples(samplesData.samples || []);
      renderVoiceJobs(jobsData.jobs || []);
      const latestStatus = (jobsData.jobs?.[0]?.status || '').toLowerCase();
      if (VOICE_ACTIVE_STATUSES.has(latestStatus)) {
        state.pollTimer = setTimeout(() => refreshVoiceTraining(projectName), 5000);
      }
    } catch (error) {
      console.error('voice_training_refresh_failed', error);
      resetVoiceTrainingUi(translate('voiceTrainingLoadError', 'Failed to load training data.'));
    }
  };

  const uploadVoiceSamples = async (projectName) => {
    if (!projectName) return;
    if (!elements.fileInput || !elements.fileInput.files?.length) {
      if (elements.uploadStatus) elements.uploadStatus.textContent = translate('voiceSelectFilesPrompt', 'Select files to upload.');
      return;
    }
    const formData = new FormData();
    formData.append('project', projectName);
    Array.from(elements.fileInput.files).forEach((file) => formData.append('files', file));
    if (elements.uploadStatus) elements.uploadStatus.textContent = translate('voiceLoading', 'Loading…');
    try {
      const response = await fetch('/api/v1/voice/samples', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || 'upload_failed');
      }
      const data = await response.json();
      renderVoiceSamples(data.samples || []);
      elements.fileInput.value = '';
      updateFileSelectionLabel();
      if (elements.uploadStatus) elements.uploadStatus.textContent = translate('voiceDone', 'Done');
    } catch (error) {
      console.error('voice_upload_failed', error);
      if (elements.uploadStatus) elements.uploadStatus.textContent = translate('voiceUploadError', 'Failed to upload samples');
    }
  };

  const deleteVoiceSample = async (sampleId) => {
    const project = (global.currentProject || '').trim();
    if (!project) return;
    try {
      const response = await fetch(`/api/v1/voice/samples/${sampleId}?project=${encodeURIComponent(project)}`, {
        method: 'DELETE',
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error('delete_failed');
      const data = await response.json();
      renderVoiceSamples(data.samples || []);
    } catch (error) {
      console.error('voice_sample_delete_failed', error);
    }
  };

  const triggerVoiceTraining = async (projectName) => {
    if (!projectName) return;
    state.jobPending = true;
    refreshVoiceTrainingState();
    if (elements.trainStatus) elements.trainStatus.textContent = translate('voicePreparing', 'Preparing…');
    try {
      const formData = new FormData();
      formData.append('project', projectName);
      const response = await fetch('/api/v1/voice/train', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
      });
      const raw = await response.text();
      let data = {};
      if (raw) {
        try {
          data = JSON.parse(raw);
        } catch (error) {
          console.warn('voice_train_parse_failed', error);
          data = {};
        }
      }
      if (!response.ok) {
        const detail = (data && typeof data === 'object' && data.detail) ? data.detail : raw;
        if (response.status === 409) {
          if (elements.trainStatus) elements.trainStatus.textContent = translate('voiceTrainingAlreadyRunning', 'Training is already running');
          await refreshVoiceTraining(projectName);
          return;
        }
        if (response.status === 400 && (detail || '').startsWith('not_enough_samples')) {
          if (elements.trainStatus) elements.trainStatus.textContent = translate('voiceAddMoreSamples', 'Add more samples');
          await refreshVoiceTraining(projectName);
          return;
        }
        throw new Error(detail || `HTTP ${response.status}`);
      }
      const detail = (data && typeof data === 'object' && data.detail) ? data.detail : '';
      if (elements.trainStatus) {
        if (detail === 'job_in_progress') {
          elements.trainStatus.textContent = translate('voiceTrainingAlreadyRunning', 'Training is already running');
        } else if (detail === 'job_resumed') {
          elements.trainStatus.textContent = translate('voiceTrainingRestart', 'Restarting training');
        } else {
          elements.trainStatus.textContent = translate('voiceTrainingStarted', 'Training started');
        }
      }
      await refreshVoiceTraining(projectName);
    } catch (error) {
      console.error('voice_train_failed', error);
      if (elements.trainStatus) elements.trainStatus.textContent = translate('voiceTrainingStartError', 'Failed to start training.');
    } finally {
      state.jobPending = false;
      refreshVoiceTrainingState();
    }
  };

  const handleLanguageApplied = () => {
    if (elements.recordButton) {
      elements.recordButton.textContent = translateRecordLabel(state.recorder.active);
    }
    if (elements.jobsContainer) {
      const placeholder = elements.jobsContainer.querySelector('[data-i18n="voiceHistoryEmpty"]');
      if (placeholder) {
        placeholder.textContent = translate('voiceHistoryEmpty', 'Training history will appear after the first run.');
      }
    }
    updateFileSelectionLabel();
    refreshVoiceTrainingState();
  };

  const bindEvents = () => {
    if (elements.uploadBtn) {
      elements.uploadBtn.addEventListener('click', () => {
        const project = (global.currentProject || '').trim();
        if (!project) {
          if (elements.uploadStatus) elements.uploadStatus.textContent = translate('voiceSelectProjectToUpload', 'Select a project to upload samples.');
          return;
        }
        uploadVoiceSamples(project);
      });
    }
    if (elements.fileInput) {
      elements.fileInput.addEventListener('change', updateFileSelectionLabel);
    }
    if (elements.recordButton) {
      if (!MEDIA_RECORDER_SUPPORTED) {
        elements.recordButton.disabled = true;
        setRecordStatus(translate('voiceRecordingUnsupported', 'Recording is not supported in this browser.'));
      } else {
        elements.recordButton.addEventListener('click', () => {
          if (!state.recorder.active) {
            startVoiceRecording();
          } else {
            stopVoiceRecording();
          }
        });
      }
    }
    if (elements.trainButton) {
      elements.trainButton.addEventListener('click', () => {
        const project = (global.currentProject || '').trim();
        if (!project) {
          if (elements.trainStatus) elements.trainStatus.textContent = translate('voiceSelectProjectForTraining', 'Select a project to start training.');
          return;
        }
        if (state.jobs.some((job) => VOICE_ACTIVE_STATUSES.has(String(job.status || '').toLowerCase()))) {
          if (elements.trainStatus) elements.trainStatus.textContent = translate('voiceTrainingAlreadyRunning', 'Training is already running');
          return;
        }
        if (state.samples.length < VOICE_MIN_SAMPLE_COUNT) {
          if (elements.trainStatus) elements.trainStatus.textContent = translate('voiceAddMoreSamples', 'Add more samples');
          return;
        }
        triggerVoiceTraining(project);
      });
    }
  };

  resetVoiceTrainingUi();
  bindEvents();
  refreshVoiceTrainingState();
  updateFileSelectionLabel();

  global.VoiceModule = {
    refresh: refreshVoiceTraining,
    reset: resetVoiceTrainingUi,
    handleLanguageApplied,
  };

  global.addEventListener('beforeunload', () => {
    clearJobsPoll();
    cleanupRecorderStream();
  });
})(window);
