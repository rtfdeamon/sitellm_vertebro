# Voice Assistant Module

Voice assistant implementation for SiteLLM Vertebro, providing real-time speech recognition, text-to-speech synthesis, and conversational dialog management.

## Overview

The voice assistant enables users to interact with the SiteLLM system through voice commands, receiving audio responses. It includes:

- **Session Management** — Create and manage voice conversation sessions
- **Speech Recognition** — Convert audio input to text (Whisper/Vosk)
- **Text-to-Speech** — Generate natural-sounding speech from text (ElevenLabs/Azure/Browser)
- **Dialog Management** — Intent recognition and context-aware responses
- **WebSocket Communication** — Real-time bidirectional audio streaming

## Architecture

```
┌─────────────────┐
│  Voice Widget   │  (Frontend - widget/voice/)
│  (TypeScript)   │
└────────┬────────┘
         │ WebSocket / REST
         ▼
┌─────────────────┐
│  Voice Router   │  (voice/router.py)
│  (FastAPI)      │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬─────────────┐
    ▼         ▼          ▼             ▼
┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│Recognizer│ │Synthesizer│ │Dialog Mgr│ │MongoDB  │
│(Whisper)│ │(TTS)      │ │(Intent) │ │(Storage)│
└────────┘ └────────┘ └──────────┘ └──────────┘
```

## Quick Start

> **For a step-by-step quick start guide, see `docs/voice_quick_start.md`**

### 1. Database Migration

Run the migration script to create required collections:

```bash
python scripts/migrate_voice_schema.py
```

### 2. Environment Configuration

Add voice-related environment variables (see `docs/voice_deployment.md` for full list):

```bash
# Required
WHISPER_MODEL=base
TTS_DEFAULT_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=your_key_here

# Optional
VOICE_SESSION_TIMEOUT=3600
VOICE_MAX_CONCURRENT_SESSIONS=100
```

### 3. Start the API

The voice router is automatically included when starting the FastAPI app:

```bash
uvicorn app:app --reload
```

### 4. Use the Voice Widget

Embed the widget in your HTML:

```html
<div id="voice-root"></div>
<script src="/widget/voice/dist/voice-widget.js"></script>
<script>
  VoiceWidget.createVoiceWidget(
    document.getElementById("voice-root"),
    {
      apiBaseUrl: "http://localhost:8000",
      project: "my-project",
      language: "ru-RU"
    }
  );
</script>
```

## API Endpoints

**Note**: This router (`voice_assistant_router`) provides real-time conversational
voice assistant capabilities. For voice training sample/job management, see the
`voice_router` in `api.py` (documented separately).

### Session Management

- `POST /api/v1/voice/session/start` — Create a new voice session
- `GET /api/v1/voice/session/{session_id}` — Get session metadata
- `DELETE /api/v1/voice/session/{session_id}` — Terminate a session
- `GET /api/v1/voice/session/{session_id}/history` — Get interaction history

### Speech Processing

- `POST /api/v1/voice/recognize` — Speech-to-text recognition
- `POST /api/v1/voice/synthesize` — Text-to-speech synthesis
- `GET /api/v1/voice/audio/{audio_id}` — Retrieve cached audio

### Dialog

- `POST /api/v1/voice/dialog/intent` — Analyze user intent
- `POST /api/v1/voice/dialog/respond` — Generate dialog response

### WebSocket

- `WS /api/v1/voice/ws/{session_id}` — Real-time bidirectional communication

### Analytics

- `GET /api/v1/voice/analytics/project/{project}` — Project-level statistics

For complete API reference, see `docs/voice_api_reference.md`.

## Module Structure

```
voice/
├── __init__.py           # Package exports
├── router.py              # FastAPI router with all endpoints
├── recognizer.py          # Speech recognition (Whisper/Vosk)
├── synthesizer.py         # TTS providers (ElevenLabs/Azure/Browser)
├── dialog_manager.py      # Intent recognition and dialog flow
└── providers/             # Provider implementations
    └── __init__.py
```

## Testing

### Backend Tests

```bash
# Run all voice tests
pytest tests/test_voice_router.py tests/test_voice_e2e.py -v

# Run specific test
pytest tests/test_voice_e2e.py::test_complete_voice_interaction_flow -v
```

### Frontend Tests

```bash
cd widget/voice
npm test
```

## Documentation

- **Quick Start**: `docs/voice_quick_start.md` — Get started in 5 minutes
- **API Reference**: `docs/voice_api_reference.md` — Complete API documentation for both voice routers
- **Deployment Guide**: `docs/voice_deployment.md` — Complete deployment instructions
- **Implementation Status**: `docs/voice_implementation_status.md` — What's complete and what's planned
- **API Primer**: `docs/voice_sessions.md` — API primer and usage examples
- **Quality Metrics**: `docs/voice_quality_metrics.md` — Performance targets and SLAs

## Development Status

✅ **Completed**:
- Session lifecycle management
- Basic speech recognition (demo implementation)
- Basic TTS synthesis (demo implementation)
- Dialog manager with intent recognition
- WebSocket infrastructure
- Frontend widget with audio recording/playback
- Comprehensive test coverage
- Database migrations
- Deployment documentation

🚧 **In Progress / Future**:
- Full Whisper integration with GPU support
- Production TTS provider integrations (ElevenLabs, Azure)
- Advanced dialog context management
- Audio visualization components
- Navigation controller for web page interaction

## Contributing

When adding new features:

1. Update tests in `tests/test_voice_*.py`
2. Add TypeScript types if modifying frontend
3. Update `docs/voice_sessions.md` for API changes
4. Run `pytest` and `npm test` before committing
5. Update this README if architecture changes

## License

Same as main SiteLLM Vertebro project.

