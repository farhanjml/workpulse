import React, { useState, useEffect, useRef, useCallback } from 'react'

function timeOptions(minutesBack = 90) {
  const now = new Date()
  const opts = []
  for (let i = 0; i <= minutesBack; i += 15) {
    const t = new Date(now - i * 60000)
    const hh = String(t.getHours()).padStart(2, '0')
    const mm = String(t.getMinutes()).padStart(2, '0')
    const val = `${hh}:${mm}`
    opts.push({ value: val, label: val + (i === 0 ? ' (now)' : '') })
  }
  return opts
}

function elapsed(startTime) {
  if (!startTime) return ''
  const now = new Date()
  const [h, m] = startTime.split(':').map(Number)
  const start = new Date(now); start.setHours(h, m, 0, 0)
  const mins = Math.max(0, Math.floor((now - start) / 60000))
  return mins < 60 ? `${mins}m` : `${Math.floor(mins/60)}h ${mins%60}m`
}

export default function PingPopup() {
  const [projects, setProjects] = useState([])
  const [tasks, setTasks] = useState([])
  const [selectedProj, setSelectedProj] = useState(0)
  const [selectedTask, setSelectedTask] = useState(0)
  const [desc, setDesc] = useState('')
  const [activeEntry, setActiveEntry] = useState(null)
  const [count, setCount] = useState(0)
  const [countdown, setCountdown] = useState(60)
  const [times, setTimes] = useState([])
  const [endTime, setEndTime] = useState('')
  const [startedAt, setStartedAt] = useState('')
  const descRef = useRef(null)
  const dismissTimer = useRef(null)
  const countdownTimer = useRef(null)

  const refresh = useCallback(async () => {
    const [projs, active, cnt] = await Promise.all([
      window.api.getProjects(),
      window.api.getActive(),
      window.api.countToday(),
    ])
    setProjects(projs)
    setTasks(projs[0]?.tasks || [])
    setActiveEntry(active)
    setCount(cnt)
    const opts = timeOptions()
    setTimes(opts)
    setEndTime(opts[0]?.value || '')
    setStartedAt(opts[0]?.value || '')
    setCountdown(60)
    clearTimeout(dismissTimer.current)
    clearInterval(countdownTimer.current)
    dismissTimer.current = setTimeout(() => window.close?.(), 60000)
    countdownTimer.current = setInterval(() => setCountdown(c => c > 0 ? c - 1 : 0), 1000)
  }, [])

  useEffect(() => {
    refresh()
    const off = window.api.on('refresh', refresh)
    const onKey = (e) => {
      if (e.key === 'Escape') window.close?.()
      if ((e.key === 'Enter') && document.activeElement === descRef.current) onLog()
    }
    window.addEventListener('keydown', onKey)
    return () => { off?.(); clearTimeout(dismissTimer.current); clearInterval(countdownTimer.current); window.removeEventListener('keydown', onKey) }
  }, [refresh])

  const onProjChange = (idx) => {
    setSelectedProj(idx)
    setTasks(projects[idx]?.tasks || [])
    setSelectedTask(0)
  }

  const onStillOn = async () => {
    await window.api.extendActive()
    window.close?.()
  }

  const onEndTask = async () => {
    await window.api.endCurrent(endTime)
    window.close?.()
  }

  const onLog = async () => {
    if (!desc.trim()) { descRef.current?.focus(); return }
    const proj = projects[selectedProj]
    if (!proj) return
    const taskType = tasks[selectedTask] || ''
    const task = taskType ? `${taskType} — ${desc}` : desc
    await window.api.logEntry({ projectId: proj.id, projectName: proj.name, task, stoppedAt: startedAt })
    window.close?.()
  }

  const hasActive = !!activeEntry

  return (
    <div style={{ padding: 0 }}>
      <div className="card" style={{ width: 400 }}>
        {/* Header */}
        <div className="card-header drag">
          <span style={{ color: '#4ade80', fontSize: 8 }}>●</span>
          <span className="label-xs" style={{ flex: 1 }}>WORKPULSE · PING</span>
          {hasActive
            ? <span style={{ fontSize: 10, color: 'var(--gold-dim)', fontFamily: 'monospace' }}>🔥 {count} entries</span>
            : <span style={{ fontSize: 10, color: 'var(--gold-dim)' }}>✦ Day start</span>
          }
        </div>

        <div style={{ padding: '14px 14px 16px' }}>
          {/* Active task section */}
          {hasActive && (
            <div style={{ marginBottom: 10 }}>
              <div className="chip" style={{ marginBottom: 8 }}>
                <span style={{ color: '#4ade80', fontSize: 8 }}>●</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--t1)' }}>
                    {activeEntry.task?.includes(' — ') ? activeEntry.task.split(' — ').slice(1).join(' — ') : activeEntry.task}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--t3)' }}>{activeEntry.project_name}</div>
                </div>
                <span style={{ fontSize: 10, color: 'var(--gold-dim)', fontFamily: 'monospace' }}>
                  {elapsed(activeEntry.start_time)}
                </span>
              </div>
              <button className="btn btn-green no-drag" style={{ width: '100%', marginBottom: 8 }} onClick={onStillOn}>
                ✓  Still on it — keep going
              </button>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button className="btn btn-red no-drag" style={{ flex: 1 }} onClick={onEndTask}>
                  ⏹  Done with this task
                </button>
                <span style={{ fontSize: 10, color: 'var(--t3)' }}>ended at</span>
                <select className="select no-drag" value={endTime} onChange={e => setEndTime(e.target.value)} style={{ width: 110 }}>
                  {times.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
            </div>
          )}

          {/* First-ping hero */}
          {!hasActive && (
            <div style={{ textAlign: 'center', padding: '4px 0 10px' }}>
              <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: 2, color: 'var(--gold-dim)', marginBottom: 2 }}>
                Good morning, {window._userName || 'there'}
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--t1)', marginBottom: 2 }}>What are you starting with?</div>
              <div style={{ fontSize: 11, color: 'var(--t2)' }}>Log your first task to kick off the day</div>
            </div>
          )}

          {/* Divider */}
          {hasActive && (
            <div className="label-xs" style={{ marginBottom: 8 }}>OR SWITCHED TO SOMETHING NEW</div>
          )}

          {/* New task form */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <input ref={descRef} className="input no-drag" placeholder="What are you working on..." value={desc} onChange={e => setDesc(e.target.value)} autoFocus />
            <select className="select no-drag" value={selectedProj} onChange={e => onProjChange(Number(e.target.value))}>
              {projects.map((p, i) => <option key={p.id} value={i}>{p.name}</option>)}
            </select>
            {tasks.length > 0 && (
              <select className="select no-drag" value={selectedTask} onChange={e => setSelectedTask(Number(e.target.value))}>
                {tasks.map((t, i) => <option key={i} value={i}>{t}</option>)}
              </select>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, color: 'var(--t3)' }}>{hasActive ? 'switched at' : 'started at'}</span>
              <div style={{ flex: 1 }} />
              <select className="select no-drag" value={startedAt} onChange={e => setStartedAt(e.target.value)} style={{ width: 110 }}>
                {times.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary no-drag" style={{ flex: 1 }} onClick={onLog}>
                {hasActive ? 'Log New Task' : 'Start Tracking'}
              </button>
              <button className="btn btn-ghost no-drag" style={{ width: 70 }} onClick={() => window.close?.()}>Skip</button>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 9.5, color: 'var(--t3)' }}>Tab · Enter · Esc</span>
              <span style={{ fontSize: 9.5, color: 'var(--t3)' }}>auto-closing in {countdown}s</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
