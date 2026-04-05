import { app, BrowserWindow, Tray, Menu, Notification, nativeImage, globalShortcut, screen, shell, ipcMain } from 'electron'
import path from 'path'
import fs from 'fs'
import { initDb, countEntriesToday, getActiveEntry, endCurrentEntry, getTotalLoggedMinutes } from './database.js'
import { get, set } from './config.js'
import { PingTimer } from './timer.js'
import { registerIpc } from './ipc.js'
import { isConfigured, syncProjectsToCache } from './clockify.js'

// ── Error logging ─────────────────────────────────────────────────────────────
function getLogPath() {
  try { return path.join(app.getPath('userData'), 'error.log') } catch { return null }
}

export function writeLog(label, err) {
  const logPath = getLogPath()
  if (!logPath) return
  const line = `[${new Date().toISOString()}] ${label}: ${err?.stack || err}\n`
  try { fs.appendFileSync(logPath, line) } catch {}
}

process.on('uncaughtException', (err) => { writeLog('uncaughtException', err) })
process.on('unhandledRejection', (err) => { writeLog('unhandledRejection', err) })

// ── Dev/Prod URL helper ───────────────────────────────────────────────────────
function winURL(windowName) {
  if (!app.isPackaged) return `http://localhost:5173/?window=${windowName}`
  return `file://${path.join(app.getAppPath(), 'out/renderer/index.html')}?window=${windowName}`
}

// ── Window factory ────────────────────────────────────────────────────────────
const wins = {}

function createWindow(name, opts) {
  // Return existing only if not destroyed
  if (wins[name] && !wins[name].isDestroyed()) return wins[name]
  if (wins[name]) delete wins[name]

  const base = {
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    show: false,
    webPreferences: {
      preload: path.join(app.getAppPath(), app.isPackaged ? 'out/preload/index.js' : 'src/preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  }
  const win = new BrowserWindow({ ...base, ...opts })
  win.loadURL(winURL(name))
  win.on('close', (e) => { if (isQuitting) return; e.preventDefault(); win.hide() })
  win.on('closed', () => { delete wins[name] })
  wins[name] = win
  return win
}

function sendToWin(name, channel, data) {
  const w = wins[name]
  if (w && !w.isDestroyed()) w.webContents.send(channel, data)
}

// ── Position helpers ──────────────────────────────────────────────────────────
function centerTop(win, yOffset = 40) {
  if (!win || win.isDestroyed()) return
  const { width } = screen.getPrimaryDisplay().workAreaSize
  const [w] = win.getSize()
  win.setPosition(Math.round((width - w) / 2), yOffset)
}

function posStatusBar(win) {
  if (!win || win.isDestroyed()) return
  const { width } = screen.getPrimaryDisplay().workAreaSize
  const [w] = win.getSize()
  win.setPosition(Math.round((width - w) / 2), -8)
}

// ── Tray ──────────────────────────────────────────────────────────────────────
let tray = null

function buildTrayIcon() {
  return nativeImage.createFromDataURL(
    `data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAA` +
    `AXNSRkIB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAADlJREFUOI1j` +
    `YGBg+M9AAmAiRuP/GYaDBUaCASMpBiAD0oNBNGiAaNA4oIEGIAMoMGCA` +
    `ZAAAbgAFAumkpKQAAAAASUVORK5CYII=`
  )
}

function buildTrayMenu(appRef) {
  return Menu.buildFromTemplate([
    { label: 'View Log',  click: () => { appRef.summaryWin?.show(); appRef.summaryWin?.focus(); sendToWin('summary', 'refresh') } },
    { label: 'Quick Log', click: () => appRef.showQuickLog() },
    { label: 'End Task',  click: () => { endCurrentEntry(); appRef.timer.onUserLogged(); appRef.refreshStatusBar() } },
    { type: 'separator' },
    { label: 'Settings',  click: () => { appRef.settingsWin?.show(); appRef.settingsWin?.focus() } },
    { type: 'separator' },
    { label: 'Open Log File', click: () => { const p = getLogPath(); if (p && fs.existsSync(p)) shell.openPath(p) } },
    { label: 'Exit',      click: () => app.quit() },
  ])
}

// ── Notifications ─────────────────────────────────────────────────────────────
function notify(title, body) {
  if (!Notification.isSupported()) return
  new Notification({ title, body, silent: true }).show()
}

// ── App ───────────────────────────────────────────────────────────────────────
class WorkPulse {
  constructor() {
    this.timer = null
    this.pingWin = null
    this.quickWin = null
    this.interruptWin = null
    this.summaryWin = null
    this.settingsWin = null
    this.statusBarWin = null
    this._eodFiredToday = false
  }

  init() {
    initDb()
    this._createAllWindows()
    this._setupTray()
    this._setupHotkeys()
    this._setupTimer()
    this._setupEodTimer()
    registerIpc({ timer: this.timer, windows: this, tray })

    if (isConfigured()) syncProjectsToCache().catch(() => {})

    setTimeout(() => {
      const name = get('USER_NAME').split(' ')[0]
      notify(`Good morning, ${name}!`, 'WorkPulse is running. Press Alt+L to log your first task.')
    }, 1500)
  }

  _createAllWindows() {
    this.pingWin = createWindow('ping', { width: 400, minHeight: 300, maxWidth: 400 })
    this.pingWin.once('ready-to-show', () => centerTop(this.pingWin))

    this.quickWin = createWindow('quick', { width: 420, minHeight: 280, maxWidth: 420 })
    this.quickWin.once('ready-to-show', () => centerTop(this.quickWin, 50))

    this.interruptWin = createWindow('interrupt', { width: 380, minHeight: 280, maxWidth: 380 })
    this.interruptWin.once('ready-to-show', () => centerTop(this.interruptWin))

    // Status bar: wide enough for expanded pill, transparent areas pass mouse through
    this.statusBarWin = createWindow('statusbar', { width: 480, height: 64, alwaysOnTop: true })
    this.statusBarWin.once('ready-to-show', () => {
      posStatusBar(this.statusBarWin)
      this.statusBarWin.show()
      this.statusBarWin.setIgnoreMouseEvents(true, { forward: true })
    })

    // IPC to toggle mouse interactivity from the renderer's hover handlers
    ipcMain.on('statusbar:interactive', () => {
      if (this.statusBarWin && !this.statusBarWin.isDestroyed())
        this.statusBarWin.setIgnoreMouseEvents(false)
    })
    ipcMain.on('statusbar:passthrough', () => {
      if (this.statusBarWin && !this.statusBarWin.isDestroyed())
        this.statusBarWin.setIgnoreMouseEvents(true, { forward: true })
    })

    this.summaryWin = createWindow('summary', {
      frame: true, transparent: false, alwaysOnTop: false,
      skipTaskbar: false, width: 680, height: 600, minWidth: 620, minHeight: 500,
      show: false,
    })

    this.settingsWin = createWindow('settings', {
      frame: true, transparent: false, alwaysOnTop: false,
      skipTaskbar: false, width: 480, height: 720, resizable: false, show: false,
    })
    this.settingsWin.on('show', () => globalShortcut.unregisterAll())
    this.settingsWin.on('hide', () => this.reregisterHotkeys())
  }

  _setupTray() {
    tray = new Tray(buildTrayIcon())
    tray.setToolTip('WorkPulse')
    tray.setContextMenu(buildTrayMenu(this))
    tray.on('double-click', () => { this.summaryWin?.show(); this.summaryWin?.focus() })
  }

  reregisterHotkeys() {
    globalShortcut.unregisterAll()
    const hotkey = get('HOTKEY') || 'Alt+L'
    const interrupt = get('INTERRUPT_HOTKEY') || 'Alt+Shift+L'
    try { globalShortcut.register(hotkey, () => this.showQuickLog()) } catch (e) { writeLog('hotkey', e) }
    try { globalShortcut.register(interrupt, () => this.showInterrupt()) } catch (e) { writeLog('hotkey', e) }
  }

  _setupHotkeys() { this.reregisterHotkeys() }

  _setupTimer() {
    this.timer = new PingTimer({
      onPing: () => this._firePing(),
      onIdle: (mins) => {
        sendToWin('statusbar', 'state', 'idle')
        notify('Welcome back!', `You were away ${mins} min. Open log to fill in the gap.`)
      },
      onOverdue: (mins) => {
        sendToWin('statusbar', 'state', 'overdue')
        tray.setContextMenu(buildTrayMenu(this))
        const name = get('USER_NAME').split(' ')[0]
        notify(`⚠ Hey ${name}!`, `You've been active ${mins} min with nothing logged. Press Alt+L!`)
      },
    })
    this.timer.start()
  }

  _setupEodTimer() {
    setInterval(() => {
      const now = new Date().toTimeString().slice(0, 5)
      const eod = get('END_OF_DAY')
      if (now === eod && !this._eodFiredToday) {
        this._eodFiredToday = true
        endCurrentEntry(now)
        this.refreshStatusBar()
        const count = countEntriesToday()
        const total = getTotalLoggedMinutes()
        const hrs = Math.floor(total / 60), mins = total % 60
        const name = get('USER_NAME').split(' ')[0]
        notify(`End of day — wrap up, ${name}!`, `${count} entries · ${hrs}hr ${mins}min tracked`)
        setTimeout(() => { this.summaryWin?.show(); this.summaryWin?.focus(); sendToWin('summary', 'refresh') }, 3000)
      }
      if (now === '00:00') this._eodFiredToday = false
    }, 60000)
  }

  _firePing() {
    sendToWin('statusbar', 'state', 'active')
    if (!this.pingWin || this.pingWin.isDestroyed()) {
      this.pingWin = createWindow('ping', { width: 400, minHeight: 300, maxWidth: 400 })
    }
    centerTop(this.pingWin)
    this.pingWin.show()
    this.pingWin.focus()
    this.pingWin.webContents.send('refresh')
  }

  showQuickLog() {
    if (!this.quickWin || this.quickWin.isDestroyed()) {
      writeLog('warn', 'quickWin was destroyed — recreating')
      this.quickWin = createWindow('quick', { width: 420, minHeight: 280, maxWidth: 420 })
    }
    centerTop(this.quickWin, 50)
    this.quickWin.show()
    this.quickWin.focus()
    this.quickWin.webContents.send('refresh')
  }

  showInterrupt() {
    if (!this.interruptWin || this.interruptWin.isDestroyed()) {
      writeLog('warn', 'interruptWin was destroyed — recreating')
      this.interruptWin = createWindow('interrupt', { width: 380, minHeight: 280, maxWidth: 380 })
    }
    centerTop(this.interruptWin)
    this.interruptWin.show()
    this.interruptWin.focus()
    this.interruptWin.webContents.send('refresh')
  }

  refreshStatusBar() {
    sendToWin('statusbar', 'state', 'active')
    sendToWin('statusbar', 'refresh')
  }
}

// ── App lifecycle ─────────────────────────────────────────────────────────────
let isQuitting = false
app.on('before-quit', () => { isQuitting = true })

app.whenReady().then(() => {
  app.setAppUserModelId('com.dotdash.workpulse')
  const wp = new WorkPulse()
  wp.init()
})

app.on('will-quit', () => globalShortcut.unregisterAll())
app.on('window-all-closed', (e) => e.preventDefault())
