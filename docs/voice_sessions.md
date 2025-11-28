Voice Assistant API Primer
==========================

> **New to the voice assistant?** Start with `docs/voice_quick_start.md` for a
> step-by-step setup guide.

This note documents the first iteration of the SiteLLM Vertebro voice assistant
API and the configuration knobs required to run it locally.  The assistant runs
alongside the existing `/api/v1/voice` admin endpoints for voice training
samples/jobs — both routers share the same prefix but expose different paths
and serve different purposes.

**Note**: The voice assistant API (`voice_assistant_router`) provides real-time
conversation capabilities, while the legacy `voice_router` in `api.py` handles
voice training sample management for fine-tuning models.

Session Lifecycle
-----------------

Endpoints implemented in `voice/router.py`:

- `POST /api/v1/voice/session/start` – create a session and receive the WebSocket
  URL. Requires body matching `VoiceSessionRequest`.
- `GET /api/v1/voice/session/{session_id}` – fetch session metadata.
- `DELETE /api/v1/voice/session/{session_id}` – terminate a session explicitly.
- `GET /api/v1/voice/session/{session_id}/history` – retrieve chronological
  interaction history (up to 200 records).
- `GET /api/v1/voice/analytics/project/{project}` – lightweight per-project
  counters (sessions, interactions, active connections).

Speech recognition, synthesis, intent and WebSocket handlers currently respond
with functional demo implementations:

- `POST /api/v1/voice/recognize` – accepts base64 audio or a text hint and
  returns `RecognitionResult`.
- `POST /api/v1/voice/synthesize` – generates demo audio, caches it in Mongo and
  exposes `GET /api/v1/voice/audio/{audio_id}` for playback.
- `POST /api/v1/voice/dialog/intent` – returns a simple heuristic intent.
- `POST /api/v1/voice/dialog/respond` – runs the stub dialog manager, logs the
  turn and returns a `ResponseMessage`.
- `WS /api/v1/voice/ws/{session_id}` – acknowledges the connection (full duplex
  streaming will arrive next).

Environment Variables
---------------------

The new subsystem relies on the following settings (add them to `.env` or
export beforehand):

```
WHISPER_MODEL=base
WHISPER_DEVICE=auto
VOSK_MODEL_PATH=./models/vosk-model-small-ru-0.22
TTS_DEFAULT_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=westeurope
VOICE_SESSION_TIMEOUT=3600
VOICE_MAX_CONCURRENT_SESSIONS=100
VOICE_CACHE_AUDIO=true
VOICE_CACHE_TTL=604800
WS_PORT=8001
WS_MAX_CONNECTIONS=1000
WS_PING_INTERVAL=30
AUDIO_SAMPLE_RATE=16000
AUDIO_CHUNK_DURATION=1.0
AUDIO_MAX_DURATION=60
DIALOG_MAX_CONTEXT_LENGTH=10
DIALOG_INTENT_CONFIDENCE_THRESHOLD=0.7
VOICE_ENABLE_COST_TRACKING=true
VOICE_COST_ALERT_THRESHOLD=100
```

The `.env.example` file is currently locked by project tooling, so keep the
snippet here for reference when editing actual deployment environments.

Voice Widget (Frontend)
-----------------------

The TypeScript voice widget is located under `widget/voice/` and provides a
client-side interface for voice interactions.  It includes:

- **WebSocket Manager** (`src/core/WebSocketManager.ts`) – handles real-time
  bidirectional communication with the backend, automatic reconnection, and
  ping/pong keepalive.

- **Audio Recorder** (`src/core/AudioRecorder.ts`) – manages microphone access
  and streams audio chunks to the backend via WebSocket.

- **Audio Player** (`src/core/AudioPlayer.ts`) – plays synthesized speech from
  the backend using the Web Audio API.

- **VoiceWidget** (`src/index.ts`) – main widget class managing session
  lifecycle, UI state transitions (idle/listening/processing/speaking/error),
  and integration with all core components.

### Usage

```html
<div id="voice-root"></div>
<script src="/voice-widget.js"></script>
<script>
  const root = document.getElementById("voice-root");
  VoiceWidget.createVoiceWidget(root, {
    apiBaseUrl: "http://localhost:8000",
    project: "default",
    language: "ru-RU",
    userId: "user123"
  });
</script>
```

### Build

```bash
cd widget/voice
npm install
npm run build  # Production build
npm run dev    # Development server with hot reload
npm test       # Run Jest tests
npm run type-check  # TypeScript type checking
```

The widget exposes a UMD bundle at `dist/voice-widget.js` that can be embedded
in any HTML page.  It requires:
- Modern browser with WebSocket support
- MediaDevices API for microphone access
- Web Audio API for playback

### Testing

Unit tests in `tests/VoiceWidget.test.ts` verify rendering, session lifecycle,
and cleanup behavior.  Mock WebSocket/fetch are used to avoid actual network
calls during tests.

Browser Testing
---------------

Complete browser-based testing for all dialog scenarios has been implemented.

### Automated Dialog Tests

**File**: `tests/test_voice_browser_dialogs.py`

These tests validate:
- Navigation intent recognition (Russian and English)
- Knowledge query intent recognition
- Multi-turn conversation context maintenance
- Session lifecycle with dialogs
- Intent confidence scores
- Error handling scenarios

**Run tests**:
```bash
pytest tests/test_voice_browser_dialogs.py -v
```

**Test Results**: ✅ 8/8 tests passing

### E2E Browser Tests

**File**: `tests/test_voice_browser_e2e.py`

Complete end-to-end tests using real HTTP server:
- Complete dialog flows
- Intent variations
- Concurrent dialogs
- Session activity tracking

**Run tests** (requires running server):
```bash
export VOICE_TEST_BASE_URL=http://localhost:8000
pytest tests/test_voice_browser_e2e.py -v
```

### Manual Browser Testing

For manual browser testing guide, see `tests/browser_test_voice_dialogs.md`.

**Test Results Summary**: See `tests/BROWSER_TESTING_COMPLETE.md`.

Testing Coverage
----------------

The voice feature includes comprehensive test coverage:

### Backend Tests

- **Unit tests** (`tests/test_voice_router.py`) – verify individual endpoint
  behavior, session lifecycle, recognition/synthesis flows, and audio caching.

- **End-to-end tests** (`tests/test_voice_e2e.py`) – validate complete workflows:
  - Full interaction flow (session → recognize → intent → dialog → synthesize)
  - Concurrent session limits
  - Audio caching with emotion-aware keys
  - Intent recognition variations
  - Error handling scenarios
  - Session expiry behavior

### Frontend Tests

- **Widget unit tests** (`widget/voice/tests/VoiceWidget.test.ts`) – verify UI
  rendering, session lifecycle, state transitions, and cleanup.

- **Component tests**:
  - `WebSocketManager.test.ts` – connection management, message routing, ping/pong
  - `AudioRecorder.test.ts` – microphone access, recording lifecycle, error handling

All tests use mocked external dependencies (WebSocket, MediaRecorder, fetch) to
avoid actual network calls or browser API access during CI.

Run tests:
```bash
# Backend
pytest tests/test_voice_router.py tests/test_voice_e2e.py

# Frontend
cd widget/voice
npm test
```

Next Steps
----------

Upcoming iterations will wire the recognizer, TTS manager, dialog manager and
WebSocket pipeline with full production implementations.  Track progress
through the TODO list and `docs/voice_quality_metrics.md` for acceptance
criteria.

