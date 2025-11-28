# Browser Testing Guide for Voice Assistant Dialogs

This guide describes how to manually test all voice assistant dialog scenarios in a browser.

## Prerequisites

1. **Start the FastAPI server**:
   ```bash
   uvicorn app:app --reload --port 8000
   ```

2. **Build the voice widget** (if not already built):
   ```bash
   cd widget/voice
   npm install
   npm run build
   ```

3. **Open the demo page**:
   Navigate to `http://localhost:8000/widget/voice/public/index.html`

## Test Scenarios

### Scenario 1: Navigation Intent (Russian)

**Steps**:
1. Open the voice widget demo page
2. Click "Start Session" button
3. Wait for session to be created (state should change to "idle")
4. Click "Start Listening" button
5. Say: "Перейди на страницу с ценами" (or type in text input if microphone not available)
6. Verify:
   - Intent is classified as "navigate"
   - Suggested action contains `{"type": "navigate", "url": "/pricing"}`
   - Response text contains navigation confirmation

**Expected Result**: Widget should recognize navigation intent and return appropriate response.

### Scenario 2: Navigation Intent (English)

**Steps**:
1. Start a new session
2. Say/type: "Navigate to pricing page"
3. Verify:
   - Intent is "navigate"
   - Confidence > 0.7
   - Suggested action is present

**Expected Result**: English navigation commands should work similarly to Russian.

### Scenario 3: Knowledge Query Intent

**Steps**:
1. Start a new session
2. Say/type: "Что такое SiteLLM?"
3. Verify:
   - Intent is "knowledge_query"
   - Response contains informative text
   - Sources array is present (may be empty in demo)

**Expected Result**: Knowledge queries should return informative responses.

### Scenario 4: Multi-Turn Conversation

**Steps**:
1. Start a new session
2. First turn: "Перейди на страницу с ценами"
3. Verify first response
4. Second turn: "Расскажи подробнее"
5. Verify:
   - Both interactions are in history
   - Context is maintained between turns
   - Responses are appropriate for each turn

**Expected Result**: Multi-turn conversations should maintain context.

### Scenario 5: Session Lifecycle

**Steps**:
1. Create session
2. Execute 3-4 dialog turns
3. Check session history via API: `GET /api/v1/voice/session/{session_id}/history`
4. Verify:
   - All user messages are logged
   - All assistant responses are logged
   - Timestamps are correct
   - Interaction types are correct

**Expected Result**: Complete interaction history should be preserved.

### Scenario 6: Error Handling

**Steps**:
1. Try to send dialog message without active session (should fail with 404)
2. Try to create session when limit is reached (should fail with 503)
3. Try invalid session ID (should fail with 404)

**Expected Result**: Errors should be handled gracefully with appropriate HTTP status codes.

## Automated Browser Testing Script

For automated testing using Playwright or similar, see `tests/test_voice_browser_dialogs.py`.

## API Endpoints to Test

### Session Management
- `POST /api/v1/voice/session/start` - Create session
- `GET /api/v1/voice/session/{session_id}` - Get session info
- `GET /api/v1/voice/session/{session_id}/history` - Get interaction history
- `DELETE /api/v1/voice/session/{session_id}` - End session

### Dialog Management
- `POST /api/v1/voice/dialog/intent` - Classify intent
- `POST /api/v1/voice/dialog/respond` - Get full dialog response

### Testing Commands

Test intent classification:
```bash
curl -X POST http://localhost:8000/api/v1/voice/dialog/intent \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Перейди на страницу с ценами",
    "project": "default",
    "context": {"current_page": "/", "previous_intents": []}
  }'
```

Test full dialog response:
```bash
# First create a session
SESSION_ID=$(curl -X POST http://localhost:8000/api/v1/voice/session/start \
  -H "Content-Type: application/json" \
  -d '{"project": "default", "language": "ru-RU"}' | jq -r '.session_id')

# Then send a dialog message
curl -X POST http://localhost:8000/api/v1/voice/dialog/respond \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"project\": \"default\",
    \"text\": \"Перейди на страницу с ценами\"
  }"
```

## Verification Checklist

- [ ] Navigation intent works in Russian
- [ ] Navigation intent works in English  
- [ ] Knowledge query intent works
- [ ] Multi-turn conversations maintain context
- [ ] Session history is preserved
- [ ] Error handling works correctly
- [ ] WebSocket connection works (if testing real-time)
- [ ] Audio playback works (if testing with synthesis)

