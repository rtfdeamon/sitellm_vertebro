Voice Assistant Quality Metrics
================================

This document defines target metrics and measurement methods for the upcoming
voice assistant subsystem so that implementation tasks can be validated against
explicit quality gates.

Speech Recognition (STT)
------------------------
- **Command accuracy ≥ 92 %** – percentage of user intents correctly inferred
  from Whisper/Vosk transcripts during regression suites (50 Russian, 30
  English prompts). Validate via annotated fixtures in `tests/voice/data/`.
- **Word error rate ≤ 12 %** – compute WER on the same fixtures; failures block
  release.
- **Latency ≤ 600 ms per 5 s chunk** – measured from audio chunk receipt to
  transcript emission over WebSocket; collect via integration tests with
  timestamped payloads.

Text-to-Speech (TTS)
--------------------
- **Synthesis latency ≤ 800 ms** for ElevenLabs/Azure and ≤ 1.5 s for fallback
  GTTS, measured server-side before caching.
- **Cache hit rate ≥ 60 %** under scripted dialogs; tracked through Prometheus
  counters `voice_tts_cache_hit_total` vs miss.
- **Audio consistency** – peak-to-average ratio within ±3 dB after
  normalization, validated by `voice/tests/test_synthesizer.py`.

Dialog & Backend
----------------
- **End-to-end response time ≤ 2.5 s** (audio chunk → TTS URL) for knowledge
  responses; instrument router spans with OpenTelemetry.
- **Session reliability 99.5 %** – ratio of successful WS sessions vs dropped
  connections per 1 000 attempts; measured in load tests.
- **Intent confidence ≥ 0.75 median** for navigation/dialog intents; track a
  rolling metric from stored interactions.

Widget & UX
-----------
- **Initial load bundle ≤ 180 KB gzipped**; verify via `webpack-bundle-analyzer`.
- **UI latency ≤ 200 ms** between state transitions (listening/thinking/
  speaking) measured with browser perf marks.
- **Microphone permission handling** – 100 % coverage of allow/deny paths in
  Jest tests; no uncaught promise rejections in CI logs.

Testing & Tooling
-----------------
- **Backend coverage ≥ 90 %** inside `tests/voice/` (pytest + coverage report).
- **Widget coverage ≥ 85 %** lines/branches via Jest + ts-jest.
- **E2E suite pass rate 100 %** across scripted conversations before merge.
- **CI duration ≤ 12 min** for voice matrices (Py + JS jobs).

Monitoring & Alerts
-------------------
- Alert when **daily TTS cost ≥ $100** (prometheus alert sourced from
  `voice_tts_cost_usd_total`).
- Alert when **cache TTL hits** drop below 30 % for 1 hour.
- Alert when **failed sessions** (HTTP 5xx / WS errors) exceed 5 per 10 min.

Recording these metrics early ensures each implementation task can attach clear
acceptance criteria and automated checks.

