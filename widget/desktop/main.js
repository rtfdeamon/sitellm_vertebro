const { app, BrowserWindow, ipcMain, nativeTheme } = require('electron');
const path = require('path');
const fs = require('fs');

const CONFIG_PATH = path.join(__dirname, 'config.json');

function readConfig() {
  const defaults = {
    width: 420,
    height: 640,
    alwaysOnTop: true,
    baseUrl: 'http://localhost:8000',
    project: '',
    voiceHint: '',
    hotword: 'Ситель, слушай',
    hotwordLocale: 'ru-RU',
    theme: 'system'
  };
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      const parsed = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
      return { ...defaults, ...parsed };
    }
  } catch (error) {
    console.error('Failed to read config.json', error);
  }
  return defaults;
}

let mainWindow;
let config = readConfig();

function applyThemePreference() {
  const source = (config.theme || 'system').toLowerCase();
  if ([ 'light', 'dark', 'system' ].includes(source)) {
    nativeTheme.themeSource = source;
  } else {
    nativeTheme.themeSource = 'system';
  }
}

function createWindow() {
  applyThemePreference();
  mainWindow = new BrowserWindow({
    width: config.width || 420,
    height: config.height || 640,
    minWidth: 360,
    minHeight: 480,
    show: false,
    alwaysOnTop: Boolean(config.alwaysOnTop),
    title: 'SiteLLM Assistant',
    backgroundColor: nativeTheme.shouldUseDarkColors ? '#10131a' : '#ffffff',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: false
    }
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.loadFile(path.join(__dirname, 'src', 'renderer', 'index.html'));

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      config = readConfig();
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

ipcMain.handle('desktop:toggle-pin', () => {
  if (!mainWindow) {
    return false;
  }
  const next = !mainWindow.isAlwaysOnTop();
  mainWindow.setAlwaysOnTop(next, 'screen-saver');
  config.alwaysOnTop = next;
  return next;
});

ipcMain.handle('desktop:is-pinned', () => {
  return mainWindow ? mainWindow.isAlwaysOnTop() : false;
});

ipcMain.handle('desktop:reload-config', () => {
  config = readConfig();
  applyThemePreference();
  return config;
});

ipcMain.on('desktop:open-devtools', () => {
  if (mainWindow) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
});

module.exports = { readConfig };
