import Database from 'better-sqlite3'
import { app } from 'electron'
import path from 'path'
import fs from 'fs'

let db

export function initDb() {
  const dir = app.getPath('userData')
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
  db = new Database(path.join(dir, 'workpulse.db'))
  db.exec(`
    CREATE TABLE IF NOT EXISTS entries (
      id              INTEGER PRIMARY KEY AUTOINCREMENT,
      date            TEXT NOT NULL,
      start_time      TEXT NOT NULL,
      end_time        TEXT,
      project_id      TEXT NOT NULL,
      project_name    TEXT NOT NULL,
      task            TEXT NOT NULL,
      notes           TEXT DEFAULT '',
      is_break        INTEGER DEFAULT 0,
      clockify_synced INTEGER DEFAULT 0,
      created_at      TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date);
  `)
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

function nowTime() {
  return new Date().toTimeString().slice(0, 5)
}

export function getActiveEntry() {
  return db.prepare(
    `SELECT * FROM entries WHERE date = ? AND end_time IS NULL AND is_break = 0 ORDER BY id DESC LIMIT 1`
  ).get(today()) ?? null
}

export function logEntry({ projectId, projectName, task, stoppedAt, notes = '' }) {
  const now = nowTime()
  const dateStr = today()
  // Close any active entry
  const active = getActiveEntry()
  if (active) {
    db.prepare(`UPDATE entries SET end_time = ? WHERE id = ?`).run(stoppedAt || now, active.id)
  }
  // Insert new active entry
  const result = db.prepare(
    `INSERT INTO entries (date, start_time, project_id, project_name, task, notes) VALUES (?, ?, ?, ?, ?, ?)`
  ).run(dateStr, stoppedAt || now, projectId, projectName, task, notes)
  return result.lastInsertRowid
}

export function extendActiveEntry() {
  const active = getActiveEntry()
  if (!active) return
  // Just mark it as "acknowledged" — no DB change needed, timer resets in main
}

export function endCurrentEntry(endTime) {
  const active = getActiveEntry()
  if (!active) return
  db.prepare(`UPDATE entries SET end_time = ? WHERE id = ?`).run(endTime || nowTime(), active.id)
}

export function logInterrupt({ projectId, projectName, task, durationMinutes }) {
  const now = new Date()
  const endTime = now.toTimeString().slice(0, 5)
  const start = new Date(now.getTime() - durationMinutes * 60 * 1000)
  const startTime = start.toTimeString().slice(0, 5)
  const result = db.prepare(
    `INSERT INTO entries (date, start_time, end_time, project_id, project_name, task) VALUES (?, ?, ?, ?, ?, ?)`
  ).run(today(), startTime, endTime, projectId, projectName, task)
  return result.lastInsertRowid
}

export function getEntries(dateStr) {
  return db.prepare(
    `SELECT * FROM entries WHERE date = ? ORDER BY start_time ASC, id ASC`
  ).all(dateStr)
}

export function countEntriesToday() {
  const row = db.prepare(
    `SELECT COUNT(*) as cnt FROM entries WHERE date = ? AND end_time IS NOT NULL AND is_break = 0`
  ).get(today())
  return row?.cnt ?? 0
}

export function getTotalLoggedMinutes(dateStr) {
  const d = dateStr || today()
  const rows = db.prepare(
    `SELECT start_time, end_time FROM entries WHERE date = ? AND end_time IS NOT NULL AND is_break = 0`
  ).all(d)
  return rows.reduce((sum, r) => {
    const [sh, sm] = r.start_time.split(':').map(Number)
    const [eh, em] = r.end_time.split(':').map(Number)
    return sum + Math.max(0, (eh * 60 + em) - (sh * 60 + sm))
  }, 0)
}

export function deleteEntry(id) {
  db.prepare(`DELETE FROM entries WHERE id = ?`).run(id)
}

export function markClockifySynced(id) {
  db.prepare(`UPDATE entries SET clockify_synced = 1 WHERE id = ?`).run(id)
}

export function getUnsyncedEntries() {
  return db.prepare(
    `SELECT * FROM entries WHERE end_time IS NOT NULL AND clockify_synced = 0 AND is_break = 0`
  ).all()
}
