import { ipcMain } from 'electron'
import * as db from './database.js'
import * as clockify from './clockify.js'
import { get, getAll, saveAll } from './config.js'

export function registerIpc({ timer, windows, tray }) {
  // ── Config ────────────────────────────────────────────────────────────────
  ipcMain.handle('config:get-all', () => getAll())
  ipcMain.handle('config:save', (_e, updates) => {
    saveAll(updates)
    // Re-register hotkeys if changed
    if (updates.HOTKEY || updates.INTERRUPT_HOTKEY) {
      windows.reregisterHotkeys()
    }
  })

  // ── Projects ──────────────────────────────────────────────────────────────
  ipcMain.handle('projects:load', () => clockify.loadProjects())
  ipcMain.handle('projects:sync', async (_e, partialCfg) => {
    // Save API credentials before syncing so user doesn't have to hit Save first
    if (partialCfg) saveAll(partialCfg)
    return clockify.syncProjectsToCache()
  })

  // ── Database ──────────────────────────────────────────────────────────────
  ipcMain.handle('db:get-active', () => db.getActiveEntry())
  ipcMain.handle('db:log-entry', (_e, data) => {
    const id = db.logEntry(data)
    timer.onUserLogged()
    clockify.pushAllUnsynced()
    return id
  })
  ipcMain.handle('db:extend-active', () => {
    db.extendActiveEntry()
    timer.onUserLogged()
  })
  ipcMain.handle('db:end-current', (_e, endTime) => {
    db.endCurrentEntry(endTime)
    timer.onUserLogged()
    clockify.pushAllUnsynced()
  })
  ipcMain.handle('db:log-interrupt', (_e, data) => {
    const id = db.logInterrupt(data)
    clockify.pushAllUnsynced()
    return id
  })
  ipcMain.handle('db:get-entries', (_e, dateStr) => db.getEntries(dateStr))
  ipcMain.handle('db:count-today', () => db.countEntriesToday())
  ipcMain.handle('db:total-minutes', (_e, dateStr) => db.getTotalLoggedMinutes(dateStr))
  ipcMain.handle('db:delete-entry', (_e, id) => db.deleteEntry(id))
}
