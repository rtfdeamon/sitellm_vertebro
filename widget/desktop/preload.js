const { contextBridge, ipcRenderer } = require('electron');
const path = require('path');
const fs = require('fs');

function loadConfig() {
  const defaults = {
    baseUrl: 'http://localhost:8000',
    project: '',
    voiceHint: '',
    orientation: 'bottom-right',
    readingMode: true,
    mode: 'avatar',
    color: '#4f7cff',
    hotword: 'Ситель, слушай',
    hotwordLocale: 'ru-RU',
    character: 'luna'
  };
  const configPath = path.join(__dirname, 'config.json');
  if (!fs.existsSync(configPath)) {
    return defaults;
  }
  try {
    const raw = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    return { ...defaults, ...raw };
  } catch (error) {
    console.error('[SiteLLM desktop] Failed to parse config.json', error);
    return defaults;
  }
}

contextBridge.exposeInMainWorld('desktopConfig', loadConfig());

contextBridge.exposeInMainWorld('desktopAPI', {
  togglePin: () => ipcRenderer.invoke('desktop:toggle-pin'),
  isPinned: () => ipcRenderer.invoke('desktop:is-pinned'),
  reloadConfig: () => ipcRenderer.invoke('desktop:reload-config'),
  openDevTools: () => ipcRenderer.send('desktop:open-devtools')
});
