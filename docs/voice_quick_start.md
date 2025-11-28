# Voice Assistant - Quick Start Guide

Get the voice assistant up and running in 5 minutes.

## Prerequisites

- MongoDB 5+ running and accessible
- Python 3.10+ with project dependencies installed
- Node.js 18+ (for widget build, optional)

## Step 1: Database Migration

Run the migration script to create required collections:

```bash
python scripts/migrate_voice_schema.py
```

You should see:
```
INFO voice_migration_completed collections_created=4 indexes_created=10
INFO voice_migration_verified
```

## Step 2: Environment Configuration

Add minimal voice configuration to your `.env` file:

```bash
# Required for basic functionality
TTS_DEFAULT_PROVIDER=browser  # Use browser TTS for quick start (free)

# Optional but recommended
WHISPER_MODEL=base
VOICE_SESSION_TIMEOUT=3600
VOICE_MAX_CONCURRENT_SESSIONS=100
```

**For production TTS** (optional, requires API keys):
```bash
TTS_DEFAULT_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=your_key_here
# or
TTS_DEFAULT_PROVIDER=azure
AZURE_SPEECH_KEY=your_key_here
AZURE_SPEECH_REGION=westeurope
```

## Step 3: Start the API

The voice router is automatically included in the main FastAPI app:

```bash
uvicorn app:app --reload
```

Verify the voice endpoints are available:
```bash
curl http://localhost:8000/api/v1/voice/analytics/project/default
```

## Step 4: Test Session Creation

Create a test voice session:

```bash
curl -X POST http://localhost:8000/api/v1/voice/session/start \
  -H "Content-Type: application/json" \
  -d '{
    "project": "default",
    "language": "ru-RU"
  }'
```

Expected response:
```json
{
  "session_id": "hex-id",
  "websocket_url": "ws://localhost:8000/api/v1/voice/ws/hex-id",
  "expires_at": "2025-11-16T...",
  "initial_greeting": "Голосовой ассистент готов. Чем могу помочь?"
}
```

## Step 5: Build Frontend Widget (Optional)

If you want to use the voice widget in your HTML pages:

```bash
cd widget/voice
npm install
npm run build
```

The built bundle will be available at `/widget/voice/dist/voice-widget.js`.

## Step 6: Embed Widget in HTML

```html
<!DOCTYPE html>
<html>
<head>
  <title>Voice Assistant Demo</title>
</head>
<body>
  <div id="voice-root"></div>
  
  <script src="/widget/voice/dist/voice-widget.js"></script>
  <script>
    VoiceWidget.createVoiceWidget(
      document.getElementById("voice-root"),
      {
        apiBaseUrl: "http://localhost:8000",
        project: "default",
        language: "ru-RU"
      }
    );
  </script>
</body>
</html>
```

## Testing

Run the test suite to verify everything works:

```bash
# Backend tests
pytest tests/test_voice_router.py tests/test_voice_e2e.py -v

# Frontend tests (if widget is built)
cd widget/voice
npm test
```

## Common Issues

### Migration Fails
- Ensure MongoDB is running and accessible
- Check connection string in `.env` or environment variables
- Verify database permissions

### Session Creation Returns 503
- Check `VOICE_MAX_CONCURRENT_SESSIONS` limit
- Verify MongoDB connection
- Check logs for detailed error messages

### WebSocket Connection Fails
- Ensure proxy/load balancer supports WebSocket upgrades
- Check firewall allows WebSocket traffic
- Verify `WS_PORT` configuration if using custom port

### Widget Not Loading
- Verify widget bundle is built: `cd widget/voice && npm run build`
- Check browser console for errors
- Ensure API base URL is correct and accessible

## Next Steps

- **Production Setup**: See `docs/voice_deployment.md` for complete deployment guide
- **API Reference**: See `docs/voice_api_reference.md` for all available endpoints
- **Quality Metrics**: See `docs/voice_quality_metrics.md` for performance targets
- **Module Documentation**: See `voice/README.md` for architecture details

## Support

For issues or questions:
1. Check the troubleshooting section in `docs/voice_deployment.md`
2. Review test files in `tests/test_voice_*.py` for usage examples
3. Inspect logs for detailed error messages

