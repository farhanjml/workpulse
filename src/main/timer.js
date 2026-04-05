import { powerMonitor } from 'electron'
import { get } from './config.js'

export class PingTimer {
  constructor({ onPing, onIdle, onOverdue }) {
    this.onPing = onPing
    this.onIdle = onIdle
    this.onOverdue = onOverdue
    this._isIdle = false
    this._lastLogTime = Date.now()
    this._nextPingTime = Date.now() + get('PING_INTERVAL') * 60 * 1000
    this._overdueFired = false
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
  }

  _poll() {
    const idleThresholdMs = get('IDLE_THRESHOLD') * 60 * 1000
    const overdueMs = get('OVERDUE_WARNING') * 60 * 1000

    let idleMs = 0
    try {
      idleMs = powerMonitor.getSystemIdleTime() * 1000
    } catch {
      idleMs = 0
    }

    if (!this._isIdle && idleMs >= idleThresholdMs) {
      this._isIdle = true
      return
    }

    if (this._isIdle && idleMs < idleThresholdMs) {
      this._isIdle = false
      const idleMinutes = Math.round(idleMs / 60000)
      this.onIdle(idleMinutes)
      this.onUserLogged() // reset ping timer after returning
      return
    }

    if (this._isIdle) return

    const now = Date.now()

    if (!this._overdueFired && now - this._lastLogTime >= overdueMs) {
      this._overdueFired = true
      this.onOverdue(Math.round((now - this._lastLogTime) / 60000))
    }

    if (now >= this._nextPingTime) {
      this._nextPingTime = now + get('PING_INTERVAL') * 60 * 1000
      this.onPing()
    }
  }
}
