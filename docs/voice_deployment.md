Voice Assistant Deployment Guide
=================================

This guide covers deployment steps for the voice assistant feature in SiteLLM
Vertebro, including database migrations, environment configuration, and production
considerations.

Prerequisites
-------------

- MongoDB 5+ with GridFS support
- Redis (for session management if using distributed deployment)
- Python 3.10+ with `uv` or `pip`
- Node.js 18+ (for building the voice widget frontend)
- Optional: GPU support for Whisper model acceleration

Database Migration
------------------

Before deploying the voice assistant, run the migration script to create required
collections and indexes:

```bash
python scripts/migrate_voice_schema.py
```

This script will:
1. Create `voice_sessions`, `voice_interactions`, `voice_audio_cache`, and
   `voice_analytics` collections
2. Create indexes for efficient queries (session lookups, TTL for auto-cleanup)
3. Verify that all collections and indexes are properly created

**Important**: The script is idempotent — it's safe to run multiple times. If
collections already exist, it will only create missing indexes.

### Collections Created

- **voice_sessions**: Active and historical voice conversation sessions
  - TTL index on `expires_at` for automatic cleanup
  - Index on `session_id` (unique), `project+created_at` for analytics

- **voice_interactions**: Log of all user-assistant interactions
  - TTL index on `timestamp` (30 days retention)
  - Indexes on `session_id+timestamp`, `project+timestamp` for queries

- **voice_audio_cache**: Cached synthesized audio files
  - TTL index on `accessed_at` (7 days retention)
  - Composite index on `text_hash+voice+language` for cache lookups

- **voice_analytics**: Future analytics data (placeholder collection)

Environment Configuration
-------------------------

Add the following environment variables to your `.env` file or deployment
configuration:

### Speech Recognition

```bash
# Whisper model selection (tiny, base, small, medium, large)
WHISPER_MODEL=base

# Device selection (auto, cpu, cuda)
WHISPER_DEVICE=auto

# Vosk offline model path (fallback)
VOSK_MODEL_PATH=./models/vosk-model-small-ru-0.22
```

### Text-to-Speech

```bash
# Default TTS provider (elevenlabs, azure, browser)
TTS_DEFAULT_PROVIDER=elevenlabs

# ElevenLabs configuration
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Azure Cognitive Services Speech
AZURE_SPEECH_KEY=your_key_here
AZURE_SPEECH_REGION=westeurope
```

### Session Management

```bash
# Session timeout in seconds (default: 1 hour)
VOICE_SESSION_TIMEOUT=3600

# Maximum concurrent voice sessions (default: 100)
VOICE_MAX_CONCURRENT_SESSIONS=100
```

### Audio Caching

```bash
# Enable audio caching (default: true)
VOICE_CACHE_AUDIO=true

# Cache TTL in seconds (default: 7 days)
VOICE_CACHE_TTL=604800
```

### WebSocket Configuration

```bash
# WebSocket port (if different from main API port)
WS_PORT=8001

# Maximum concurrent WebSocket connections (default: 1000)
WS_MAX_CONNECTIONS=1000

# Ping interval in seconds (default: 30)
WS_PING_INTERVAL=30
```

### Audio Processing

```bash
# Audio sample rate in Hz (default: 16000)
AUDIO_SAMPLE_RATE=16000

# Chunk duration in seconds (default: 1.0)
AUDIO_CHUNK_DURATION=1.0

# Maximum audio duration in seconds (default: 60)
AUDIO_MAX_DURATION=60
```

### Dialog Settings

```bash
# Maximum context length in turns (default: 10)
DIALOG_MAX_CONTEXT_LENGTH=10

# Intent confidence threshold (default: 0.7)
DIALOG_INTENT_CONFIDENCE_THRESHOLD=0.7
```

### Cost Tracking

```bash
# Enable cost tracking for TTS providers (default: true)
VOICE_ENABLE_COST_TRACKING=true

# Daily cost alert threshold in USD (default: 100)
VOICE_COST_ALERT_THRESHOLD=100
```

### MongoDB Collection Names (Optional Overrides)

```bash
MONGO_VOICE_SESSIONS=voice_sessions
MONGO_VOICE_INTERACTIONS=voice_interactions
MONGO_VOICE_AUDIO_CACHE=voice_audio_cache
MONGO_VOICE_ANALYTICS=voice_analytics
```

Dependencies Installation
-------------------------

### Backend

Install Python dependencies (including voice assistant packages):

```bash
uv sync
# or
pip install -e .
```

Key voice-related packages:
- `openai-whisper>=20231117` — Whisper speech recognition
- `faster-whisper>=1.0.0` — Optimized Whisper implementation
- `vosk>=0.3.45` — Offline speech recognition (optional)
- `elevenlabs>=0.2.0` — ElevenLabs TTS provider
- `azure-cognitiveservices-speech>=1.34.0` — Azure TTS provider

### Frontend Widget

Build the voice widget:

```bash
cd widget/voice
npm install
npm run build
```

The built bundle (`dist/voice-widget.js`) is automatically served by FastAPI
static file mounting at `/widget/voice/dist/voice-widget.js`.

Docker Compose Deployment
-------------------------

The voice assistant integrates with the existing `compose.yaml`. No additional
services are required if using the main API container.

### Optional: Separate Voice Worker

If you want to run voice processing in a separate container (useful for GPU
acceleration), add to `compose.yaml`:

```yaml
voice-worker:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: sitellm-voice-worker
  depends_on:
    - mongo
    - redis
  environment:
    - MONGO_HOST=mongo
    - REDIS_HOST=redis
    - WHISPER_MODEL=base
    - WHISPER_DEVICE=cuda  # Use GPU if available
  volumes:
    - ./voice:/app/voice:ro
    - voice-models:/app/models
  command: python -m voice.worker
  restart: unless-stopped
  networks:
    - sitellm-network

volumes:
  voice-models:
    driver: local
```

Production Checklist
--------------------

- [ ] Run database migration (`scripts/migrate_voice_schema.py`)
- [ ] Configure TTS provider API keys (ElevenLabs or Azure)
- [ ] Set `VOICE_MAX_CONCURRENT_SESSIONS` based on expected load
- [ ] Configure `VOICE_SESSION_TIMEOUT` for your use case
- [ ] Set up monitoring for voice session metrics
- [ ] Configure cost alerts if using paid TTS providers
- [ ] Test WebSocket connectivity through load balancer/proxy
- [ ] Build and deploy voice widget frontend
- [ ] Verify audio caching is working (check GridFS usage)
- [ ] Set up log aggregation for voice interactions
- [ ] Test end-to-end: session creation → recognition → synthesis

Monitoring & Metrics
--------------------

The voice assistant exposes metrics via Prometheus:

- `voice_sessions_active` — Current active session count
- `voice_sessions_created_total` — Total sessions created
- `voice_interactions_total` — Total interactions logged
- `voice_audio_cache_hits_total` — Cache hit count
- `voice_audio_cache_misses_total` — Cache miss count
- `voice_synthesis_duration_seconds` — TTS generation time
- `voice_recognition_duration_seconds` — STT processing time

Monitor these metrics to:
- Detect session leaks (active sessions not expiring)
- Track cache effectiveness (hit/miss ratio)
- Identify performance bottlenecks (synthesis/recognition duration)
- Alert on unusual traffic spikes

Troubleshooting
---------------

### WebSocket Connection Failures

If WebSocket connections fail:
1. Verify proxy/load balancer supports WebSocket upgrades
2. Check `WS_PORT` matches your deployment configuration
3. Ensure firewall allows WebSocket traffic (port 8001 or custom)

### Audio Caching Not Working

If audio is not being cached:
1. Verify GridFS is accessible and writable
2. Check `VOICE_CACHE_AUDIO=true` in environment
3. Inspect MongoDB logs for GridFS upload errors

### High Memory Usage

If voice processing consumes excessive memory:
1. Reduce `WHISPER_MODEL` size (base → tiny)
2. Lower `VOICE_MAX_CONCURRENT_SESSIONS`
3. Enable audio cache TTL cleanup
4. Consider separate voice worker container with resource limits

### TTS Provider Errors

If synthesis fails:
1. Verify API keys are correct and have quota remaining
2. Check provider service status
3. Review logs for specific error messages
4. Enable fallback provider in configuration

Rollback Procedure
------------------

If you need to rollback the voice assistant feature:

1. **Disable voice endpoints** — Remove router from `app.py`:
   ```python
   # app.include_router(voice_assistant_router, prefix="/api/v1")
   ```

2. **Stop voice worker** (if running separately):
   ```bash
   docker compose stop voice-worker
   ```

3. **Collections remain** — Voice collections in MongoDB will persist but won't
   be accessed. You can optionally drop them:
   ```javascript
   // In MongoDB shell
   db.voice_sessions.drop()
   db.voice_interactions.drop()
   db.voice_audio_cache.drop()
   ```

4. **Remove frontend widget** — Delete or comment out widget mounting in HTML
   pages.

The migration script and voice collections are non-intrusive and don't affect
existing functionality if left in place.

