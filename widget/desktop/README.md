# SiteLLM Desktop Assistant

Electron-based shell that wraps the `widget/voice-avatar.js` experience into an always-on-top desktop companion for Linux and Windows.

## Features

- Runs the SiteLLM voice avatar in a standalone window that floats above other applications.
- Optional hotword detection (default `"Ситель, слушай"`) to trigger microphone capture without using the mouse.
- Shares the same animated characters and reading mode as the web widget.
- Per-platform build targets (`AppImage`/`deb` for Linux, NSIS installer for Windows).

## Prerequisites

- Node.js ≥ 18
- Yarn or npm
- For hotword capture you need the system microphone and, on Linux, speech-dispatcher (`sudo apt install speech-dispatcher`).

## Development

```bash
cd widget/desktop
npm install
npm run dev
```

The command launches Electron in watch mode (`electronmon`). Configuration is read from `config.json` (copied at start-up); restart the app to apply changes.

## Settings (`config.json`)

```json
{
  "baseUrl": "http://localhost:8000", // Backend API origin
  "project": "vertebro",              // Project slug (optional)
  "voiceHint": "Марина",              // Voice hint for speech synthesis
  "orientation": "bottom-right",      // any corner: bottom-right, bottom-left, top-right, top-left
  "readingMode": true,                 // enable reading/book previews by default
  "mode": "avatar",                   // avatar | voice | text
  "color": "#4f7cff",                 // widget accent colour
  "hotword": "Ситель, слушай",        // wake phrase
  "hotwordLocale": "ru-RU",           // recognition locale
  "character": "luna",                // default animated persona
  "alwaysOnTop": true,                 // pin window above others
  "width": 420,
  "height": 640,
  "theme": "system"                   // light | dark | system
}
```

## Packaging

### Linux

```bash
npm run build:linux
```

Outputs AppImage and `.deb` packages in the `dist` directory.

To expose the artifacts through the `/widget` page, copy them to:

- `widget/desktop/dist/Linux/SiteLLMAssistant-x86_64.AppImage`
- `widget/desktop/dist/Linux/sitellm-assistant_amd64.deb`

### Windows

```bash
npm run build:windows
```

Generates an NSIS installer (`.exe`) and portable build under `dist/`.

Copy the installer to `widget/desktop/dist/Windows/SiteLLMAssistant-Setup.exe` for the download link to work.

> Tip: Run `npm run build` on the target OS for native artifacts.

## Hotword usage

- The lower status bar shows the current wake phrase and a toggle to pause listening.
- When the phrase is detected, the app activates the microphone button inside the widget.
- Desktop environments may request microphone permission the first time you run the assistant.

## Troubleshooting

- **No speech recognition**: ensure the OS exposes the microphone to Chromium. On Linux launch with `--enable-speech-dispatcher` if the default driver is unavailable.
- **Widget fails to load**: verify `baseUrl` and `project` in `config.json`, or open DevTools via the 🛠️ action to inspect console output.
- **Packaging on ARM**: adjust `electron-builder` targets in `package.json` to match your architecture.

## License

MIT
