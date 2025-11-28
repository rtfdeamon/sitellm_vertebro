# Voice API Reference

Complete API reference for both voice-related routers in SiteLLM Vertebro.

> **Implementation Status**: The voice assistant API is production-ready for session
> management, speech recognition/synthesis, and dialog management. WebSocket streaming
> endpoints have infrastructure in place and are ready for full implementation.

## Router Overview

There are two separate voice-related routers that serve different purposes:

1. **Voice Assistant Router** (`voice/router.py`) — Real-time conversational voice assistant
   - Session management
   - Speech recognition and synthesis
   - Dialog management
   - WebSocket communication

2. **Voice Training Router** (`api.py` — `voice_router`) — Voice model training management
   - Voice sample uploads
   - Training job management
   - Training status tracking

Both routers are mounted at `/api/v1/voice` but expose different endpoints.

---

## Voice Assistant API

**Router**: `voice/router.py`  
**Prefix**: `/api/v1/voice`  
**Tag**: `voice assistant`

### Session Management

#### POST /api/v1/voice/session/start

Create a new voice conversation session.

**Request Body**:
```json
{
  "project": "string (required)",
  "user_id": "string (optional)",
  "language": "ru-RU (default)",
  "voice_preference": {
    "provider": "elevenlabs",
    "voice_id": "default"
  }
}
```

**Response** (201 Created):
```json
{
  "session_id": "uuid-hex",
  "websocket_url": "wss://host/api/v1/voice/ws/{session_id}",
  "expires_at": "2025-11-16T12:00:00Z",
  "initial_greeting": "Голосовой ассистент готов. Чем могу помочь?"
}
```

#### GET /api/v1/voice/session/{session_id}

Retrieve session metadata.

**Response** (200 OK):
```json
{
  "session_id": "uuid-hex",
  "websocket_url": "wss://host/api/v1/voice/ws/{session_id}",
  "expires_at": "2025-11-16T12:00:00Z",
  "initial_greeting": "Голосовой ассистент готов..."
}
```

#### DELETE /api/v1/voice/session/{session_id}

Terminate a voice session.

**Response** (204 No Content)

#### GET /api/v1/voice/session/{session_id}/history

Get interaction history for a session.

**Query Parameters**:
- `limit` (optional, default: 50, max: 200) — Number of history items

**Response** (200 OK):
```json
{
  "session_id": "uuid-hex",
  "items": [
    {
      "session_id": "uuid-hex",
      "project": "demo",
      "user_id": "u1",
      "timestamp": "2025-11-16T11:00:00Z",
      "type": "recognition",
      "content": {"text": "Hello"}
    }
  ]
}
```

### Speech Recognition

#### POST /api/v1/voice/recognize

Convert audio to text.

**Request Body**:
```json
{
  "audio_base64": "base64-encoded-audio (optional)",
  "text_hint": "string (optional, used if provided)",
  "language": "ru-RU (default)"
}
```

**Response** (200 OK):
```json
{
  "text": "Recognized text",
  "confidence": 0.92,
  "language": "ru-RU",
  "processing_time_ms": 245.0,
  "alternatives": null
}
```

### Speech Synthesis

#### POST /api/v1/voice/synthesize

Convert text to speech audio.

**Request Body**:
```json
{
  "text": "Text to synthesize",
  "voice": "default",
  "language": "ru-RU",
  "emotion": "neutral",
  "options": {}
}
```

**Response** (202 Accepted):
```json
{
  "audio_url": "/api/v1/voice/audio/{audio_id}",
  "duration_seconds": 5.2,
  "cached": false
}
```

#### GET /api/v1/voice/audio/{audio_id}

Retrieve cached audio file.

**Response** (200 OK):
- Content-Type: `audio/mpeg`
- Body: Binary audio data

### Dialog Management

#### POST /api/v1/voice/dialog/intent

Analyze user intent from text.

**Request Body**:
```json
{
  "text": "Покажи мне раздел с ценами",
  "project": "demo",
  "context": {
    "current_page": "/",
    "previous_intents": []
  }
}
```

**Response** (200 OK):
```json
{
  "intent": "navigate",
  "confidence": 0.95,
  "entities": {
    "target_section": "pricing"
  },
  "suggested_action": {
    "type": "navigate",
    "url": "/pricing"
  }
}
```

#### POST /api/v1/voice/dialog/respond

Generate dialog response.

**Request Body**:
```json
{
  "session_id": "uuid-hex",
  "project": "demo",
  "text": "User question text"
}
```

**Response** (202 Accepted):
```json
{
  "text": "Assistant response text",
  "audio_url": "/api/v1/voice/audio/{audio_id}",
  "sources": [],
  "suggested_actions": []
}
```

### WebSocket

#### WS /api/v1/voice/ws/{session_id}

Real-time bidirectional communication for voice interactions.

> **Status**: WebSocket endpoint accepts connections and acknowledges them.
> Full audio streaming implementation is ready for integration with production
> recognizer/synthesizer providers.

**Client Messages**:
```json
{"type": "audio_chunk", "data": "base64", "sequence": 0, "is_final": false}
{"type": "text_input", "text": "User text"}
{"type": "navigation_command", "action": "scroll", "params": {}}
{"type": "ping"}
```

**Server Messages**:
```json
{"type": "transcription", "text": "...", "is_final": true, "confidence": 0.9}
{"type": "response", "text": "...", "audio_url": "...", "sources": []}
{"type": "status", "status": "thinking", "message": "Обрабатываю..."}
{"type": "pong"}
{"type": "error", "message": "Error description"}
```

### Analytics

#### GET /api/v1/voice/analytics/project/{project}

Get project-level voice statistics.

**Response** (200 OK):
```json
{
  "project": "demo",
  "sessions_total": 150,
  "interactions_total": 1250,
  "active_sessions": 5,
  "ws_max_connections": 1000,
  "ws_ping_interval": 30
}
```

---

## Voice Training API

**Router**: `api.py` — `voice_router`  
**Prefix**: `/api/v1/voice`  
**Tag**: `voice`

### Voice Samples

#### GET /api/v1/voice/samples

List voice training samples for a project.

**Query Parameters**:
- `project` (optional) — Project identifier

**Response** (200 OK):
```json
{
  "samples": [
    {
      "id": "sample-id",
      "project": "demo",
      "file_id": "gridfs-file-id",
      "filename": "sample.wav",
      "content_type": "audio/wav",
      "size_bytes": 102400,
      "duration_seconds": 5.0,
      "uploaded_at": 1700000000.0
    }
  ]
}
```

#### POST /api/v1/voice/samples

Upload voice training samples.

**Form Data**:
- `project` (required) — Project identifier
- `files` (required) — Audio files (multipart/form-data)

**Response** (200 OK):
```json
{
  "samples": [...]
}
```

#### DELETE /api/v1/voice/samples/{sample_id}

Delete a voice training sample.

**Response** (200 OK):
```json
{
  "samples": [...]
}
```

### Training Jobs

#### GET /api/v1/voice/jobs

List voice training jobs.

**Query Parameters**:
- `project` (optional) — Project identifier
- `limit` (optional, default: 10, max: 25) — Number of jobs

**Response** (200 OK):
```json
{
  "jobs": [
    {
      "id": "job-id",
      "project": "demo",
      "status": "completed",
      "progress": 100.0,
      "message": "Training completed",
      "created_at": 1700000000.0,
      "started_at": 1700000100.0,
      "finished_at": 1700003600.0
    }
  ]
}
```

#### GET /api/v1/voice/status

Get current training status for a project.

**Query Parameters**:
- `project` (optional) — Project identifier

**Response** (200 OK):
```json
{
  "job": {
    "id": "job-id",
    "project": "demo",
    "status": "training",
    "progress": 45.0,
    "message": "Training in progress..."
  }
}
```

#### POST /api/v1/voice/train

Start a voice training job.

**Form Data**:
- `project` (required) — Project identifier

**Response** (200 OK):
```json
{
  "job": {
    "id": "job-id",
    "project": "demo",
    "status": "queued",
    "progress": 0.0,
    "message": "Job queued",
    "created_at": 1700000000.0
  }
}
```

---

## Error Responses

All endpoints may return standard HTTP error codes:

- **400 Bad Request** — Invalid request parameters
- **404 Not Found** — Resource not found (session, audio, etc.)
- **415 Unsupported Media Type** — Invalid audio format
- **422 Unprocessable Entity** — Validation errors
- **503 Service Unavailable** — Service overloaded or unavailable

**Error Response Format**:
```json
{
  "detail": "Error message description"
}
```

---

## Rate Limiting

- **Session Creation**: Limited by `VOICE_MAX_CONCURRENT_SESSIONS` (default: 100)
- **WebSocket Connections**: Limited by `WS_MAX_CONNECTIONS` (default: 1000)
- **Audio Caching**: Automatic TTL cleanup (7 days for accessed_at)

---

## Authentication

Voice assistant endpoints require HTTP Basic Auth (same as main API).  
WebSocket connections inherit authentication from the session creation request.

