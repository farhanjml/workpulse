import { ipcMain } from 'electron'
import * as db from './database.js'
import * as clockify from './clockify.js'
import { get, set, getAll, saveAll } from './config.js'

export function registerIpc({ getTimer, windows, tray }) {
  // ── Config ────────────────────────────────────────────────────────────────
  ipcMain.handle('config:get-all', () => getAll())
  ipcMain.handle('config:save', (_e, updates) => {
    saveAll(updates)
    if (updates.HOTKEY || updates.INTERRUPT_HOTKEY) windows.reregisterHotkeys()
  })
  ipcMain.handle('config:toggle-theme', () => {
    const isDark = !get('DARK_MODE')
    set('DARK_MODE', isDark)
    windows.broadcastTheme(isDark)
    return isDark
  })

  // ── Projects ──────────────────────────────────────────────────────────────
  ipcMain.handle('projects:load', () => clockify.loadProjects())
  ipcMain.handle('workspaces:fetch', async (_e, apiKey) => {
    if (apiKey) saveAll({ CLOCKIFY_API_KEY: apiKey })
    try {
      return { ok: true, workspaces: await clockify.fetchWorkspaces() }
    } catch (e) {
      const status = e?.response?.status
      const msg = e?.response?.data?.message || e?.message || String(e)
      return { ok: false, error: `HTTP ${status || '?'}: ${msg}` }
    }
  })
  ipcMain.handle('projects:sync', async (_e, partialCfg) => {
    if (partialCfg) saveAll(partialCfg)
    return clockify.syncProjectsToCache()
  })

  // ── Database ──────────────────────────────────────────────────────────────
  ipcMain.handle('db:get-active', () => db.getActiveEntry())
  ipcMain.handle('db:log-entry', (_e, data) => {
    const id = db.logEntry(data)
    getTimer()?.onUserLogged()
    windows.refreshStatusBar()
    clockify.pushAllUnsynced()
    return id
  })
  ipcMain.handle('db:extend-active', () => {
    db.extendActiveEntry()
    getTimer()?.onUserLogged()
    windows.refreshStatusBar()
  })
  ipcMain.handle('db:end-current', (_e, endTime) => {
    db.endCurrentEntry(endTime)
    getTimer()?.onUserLogged()
    windows.refreshStatusBar()
    clockify.pushAllUnsynced()
  })
  ipcMain.handle('db:log-interrupt', (_e, data) => {
    const id = db.logInterrupt(data)
    windows.refreshStatusBar()
    clockify.pushAllUnsynced()
    return id
  })
  ipcMain.handle('db:get-entries', (_e, dateStr) => db.getEntries(dateStr))
  ipcMain.handle('db:count-today', () => db.countEntriesToday())
  ipcMain.handle('db:total-minutes', (_e, dateStr) => db.getTotalLoggedMinutes(dateStr))
  ipcMain.handle('db:delete-entry', (_e, id) => db.deleteEntry(id))
}
