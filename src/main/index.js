import { app, BrowserWindow, Tray, Menu, Notification, nativeImage, globalShortcut, screen } from 'electron'
import path from 'path'
import { initDb, countEntriesToday, getActiveEntry, endCurrentEntry, getTotalLoggedMinutes } from './database.js'
import { get, set } from './config.js'
import { PingTimer } from './timer.js'
import { registerIpc } from './ipc.js'
import { isConfigured, syncProjectsToCache } from './clockify.js'

// ── Dev/Prod URL helper ───────────────────────────────────────────────────────
function winURL(windowName) {
  if (!app.isPackaged) {
    return `http://localhost:5173/?window=${windowName}`
  }
  return `file://${path.join(app.getAppPath(), 'out/renderer/index.html')}?window=${windowName}`
}

// ── Window factory ────────────────────────────────────────────────────────────
const wins = {}

function createWindow(name, opts) {
  if (wins[name]) return wins[name]
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
  win.on('close', (e) => { e.preventDefault(); win.hide() })
  wins[name] = win
  return win
}

function getWin(name) { return wins[name] ?? null }

function showWin(name) {
  const w = getWin(name)
  if (!w) return
  w.show()
  w.focus()
}

function sendToWin(name, channel, data) {
  const w = getWin(name)
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
  const { width } = screen.getPrimaryDisplay().workAreaSize
  const [w] = win.getSize()
  win.setPosition(Math.round((width - w) / 2), -8)
}

// ── Tray ──────────────────────────────────────────────────────────────────────
let tray = null

function buildTrayIcon(state = 'idle') {
  const colors = { active: '#4ade80', idle: '#e9bb51', overdue: '#ef4444' }
  const c = colors[state] || colors.idle
  // 16x16 transparent icon with colored dot — fallback to empty if icon files not found
  const img = nativeImage.createFromDataURL(
    `data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAA` +
    `AXNSRkIB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAADlJREFUOI1j` +
    `YGBg+M9AAmAiRuP/GYaDBUaCASMpBiAD0oNBNGiAaNA4oIEGIAMoMGCA` +
    `ZAAAbgAFAumkpKQAAAAASUVORK5CYII=`
  )
  return img
}

function buildTrayMenu(appRef) {
  return Menu.buildFromTemplate([
    { label: 'View Log',   click: () => { appRef.summaryWin?.show(); appRef.summaryWin?.focus(); sendToWin('summary', 'refresh') } },
    { label: 'Quick Log',  click: () => appRef.showQuickLog() },
    { label: 'End Task',   click: () => { endCurrentEntry(); appRef.timer.onUserLogged(); appRef.refreshStatusBar() } },
    { type: 'separator' },
    { label: 'Settings',   click: () => { appRef.settingsWin?.show(); appRef.settingsWin?.focus() } },
    { type: 'separator' },
    { label: 'Exit',       click: () => app.quit() },
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

    // Startup sync
    if (isConfigured()) {
      syncProjectsToCache().catch(() => {})
    }

    // Greeting
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

    this.statusBarWin = createWindow('statusbar', { width: 64, height: 64, alwaysOnTop: true })
    this.statusBarWin.once('ready-to-show', () => {
      posStatusBar(this.statusBarWin)
      this.statusBarWin.show()
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
    // Suspend global hotkeys while Settings is visible so key capture works cleanly
    this.settingsWin.on('show', () => globalShortcut.unregisterAll())
    this.settingsWin.on('hide', () => this.reregisterHotkeys())
  }

  _setupTray() {
    tray = new Tray(buildTrayIcon('idle'))
    tray.setToolTip('WorkPulse')
    tray.setContextMenu(buildTrayMenu(this))
    tray.on('double-click', () => { this.summaryWin?.show(); this.summaryWin?.focus() })
  }

  _setupHotkeys() {
    this.reregisterHotkeys()
  }

  reregisterHotkeys() {
    globalShortcut.unregisterAll()
    const hotkey = get('HOTKEY') || 'Alt+L'
    const interrupt = get('INTERRUPT_HOTKEY') || 'Alt+Shift+L'
    try { globalShortcut.register(hotkey, () => this.showQuickLog()) } catch {}
    try { globalShortcut.register(interrupt, () => this.showInterrupt()) } catch {}
  }

  _setupTimer() {
    this.timer = new PingTimer({
      onPing: () => {
        this._firePing()
      },
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
    centerTop(this.pingWin)
    this.pingWin.show()
    this.pingWin.focus()
    this.pingWin.webContents.send('refresh')
  }

  showQuickLog() {
    centerTop(this.quickWin, 50)
    this.quickWin.show()
    this.quickWin.focus()
    this.quickWin.webContents.send('refresh')
  }

  showInterrupt() {
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
app.whenReady().then(() => {
  app.setAppUserModelId('com.dotdash.workpulse')
  const wp = new WorkPulse()
  wp.init()
})

app.on('will-quit', () => globalShortcut.unregisterAll())
app.on('window-all-closed', (e) => e.preventDefault()) // keep running in tray
