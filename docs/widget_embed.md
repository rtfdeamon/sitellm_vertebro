Widget Embedding Guide
======================

This guide covers two drop-in experiences for external websites:

1. **AI Consultant Widget** – a floating or inline chat powered by the existing
   `/widget/index.html` page.
2. **Voice Avatar** – an animated orb with microphone controls that streams
   replies from `/api/v1/llm/chat` and reads responses aloud.

All snippets assume the SiteLLM deployment is reachable at
`https://example.com`. Replace the URL and `data-project` slug with values that
exist in your environment.

AI Consultant Widget
--------------------

### Floating bubble launcher (default)

```html
<script
  src="https://example.com/widget/widget-loader.js"
  data-base-url="https://example.com"
  data-project="acme"
  data-variant="floating"
  data-title="AI Consultant"
  data-subtitle="Ask me anything"
  data-icon="AI"
  data-color="#4f7cff">
</script>
```

* A pulsating bubble appears in the bottom-right corner.
* Clicking the bubble opens the chat window with `/widget/index.html?embed=1`.
* Supported data attributes:
  * `data-base-url` – origin that serves the API and widget assets.
  * `data-project` – optional project slug (maps to the admin dashboard).
  * `data-color` – primary colour in HEX (used for glow/animation).
  * `data-width`, `data-height` – override the default frame size (`380x640`).
  * `data-theme` – pass `dark` or `light` to preselect the widget theme.
  * `data-debug="1"` – forwards the flag to the SSE endpoint.

### Inline panel

```html
<div class="faq-section">
  <h2>Need personalised help?</h2>
  <script
    src="https://example.com/widget/widget-loader.js"
    data-base-url="https://example.com"
    data-project="acme"
    data-variant="inline"
    data-width="100%"
    data-height="520px"
    data-color="#06b6d4">
  </script>
</div>
```

The loader replaces the `<script>` tag with a framed card that stretches to the
provided width/height. Use this when you need a static chat panel inside the
page layout.

Voice-Enabled Avatar
--------------------

Add an animated orb that listens via the Web Speech API and streams responses
through `/api/v1/llm/chat`.

```html
<section id="assistant">
  <script
    src="https://example.com/widget/voice-avatar.js"
    data-base-url="https://example.com"
    data-project="acme"
    data-lang="ru-RU"
    data-voice="Milena"
    data-label="AI"
    data-headline="AI Consultant"
    data-subtitle="Talk to me using your voice"
    data-color="#22c55e">
  </script>
</section>
```

Behaviour highlights:

* Uses browser speech recognition (`SpeechRecognition`/`webkitSpeechRecognition`)
  when available, falling back to a manual text form.
* Streams tokens via `EventSource` and reads the aggregated reply aloud using
  `speechSynthesis`. Pass `data-voice` with a speech-synthesis voice name or
  locale to steer the voice selection.
* Stores a session identifier in `localStorage` so conversations retain context.

Cross-Origin Notes
------------------

* Enable CORS for `GET /api/v1/llm/chat` and `GET /widget/index.html` when the
  snippets are embedded on third-party domains.
* Both loaders request microphone permissions. Ensure your deployment uses
  HTTPS so browsers accept microphone access.

Versioning & Customisation
--------------------------

* `widget-loader.js` and `voice-avatar.js` expose their versions via the global
  objects `SiteLLMWidgetLoader.version` and `SiteLLMVoiceAvatar.version` respectively.
* Extend the scripts or override the generated styles by loading your own CSS
  **after** the snippets. Classes prefixed with `sitellm-` are namespaced to
  avoid collisions with host pages.
