import { powerMonitor } from 'electron'
import { get } from './config.js'
import { getActiveEntry } from './database.js'

const NO_TASK_REMINDER_MS = 30 * 60 * 1000  // ping every 30 min when nothing is logged

export class PingTimer {
  constructor({ onPing, onIdle, onOverdue }) {
    this.onPing = onPing
    this.onIdle = onIdle
    this.onOverdue = onOverdue
    this._isIdle = false
    this._lastLogTime = Date.now()
    this._nextPingTime = Date.now() + get('PING_INTERVAL') * 60 * 1000
    this._overdueFired = false
    this._lastNoTaskPing = 0
    this._interval = null
  }

  start() {
    this._interval = setInterval(() => this._poll(), 5000)
  }

  stop() {
    if (this._interval) clearInterval(this._interval)
  }

  onUserLogged() {
    this._lastLogTime = Date.now()
    this._nextPingTime = Date.now() + get('PING_INTERVAL') * 60 * 1000
    this._overdueFired = false
    this._lastNoTaskPing = 0
  }

  _poll() {
    const idleThresholdMs = get('IDLE_THRESHOLD') * 60 * 1000

    let idleMs = 0
    try { idleMs = powerMonitor.getSystemIdleTime() * 1000 } catch { idleMs = 0 }

    // Idle detection
    if (!this._isIdle && idleMs >= idleThresholdMs) {
      this._isIdle = true
      return
    }
    if (this._isIdle && idleMs < idleThresholdMs) {
      this._isIdle = false
      const idleMinutes = Math.round(idleMs / 60000)
      this.onIdle(idleMinutes)
      this.onUserLogged()
      return
    }
    if (this._isIdle) return

    const now = Date.now()
    let active = null
    try { active = getActiveEntry() } catch { return }

    if (active) {
      // Has active task — ping on interval, warn if overdue
      this._lastNoTaskPing = 0

      const overdueMs = get('OVERDUE_WARNING') * 60 * 1000
      if (!this._overdueFired && now - this._lastLogTime >= overdueMs) {
        this._overdueFired = true
        this.onOverdue(Math.round((now - this._lastLogTime) / 60000))
      }

      if (now >= this._nextPingTime) {
        this._nextPingTime = now + get('PING_INTERVAL') * 60 * 1000
        this.onPing()
      }
    } else {
      // No active task — remind every 30 min
      const sinceLastEvent = now - Math.max(this._lastLogTime, this._lastNoTaskPing)
      if (sinceLastEvent >= NO_TASK_REMINDER_MS) {
        this._lastNoTaskPing = now
        this.onPing()
      }
    }
  }
}
