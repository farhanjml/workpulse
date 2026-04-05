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

export default function QuickLog() {
  const [projects, setProjects] = useState([])
  const [tasks, setTasks] = useState([])
  const [selectedProj, setSelectedProj] = useState(0)
  const [selectedTask, setSelectedTask] = useState(0)
  const [desc, setDesc] = useState('')
  const [activeEntry, setActiveEntry] = useState(null)
  const [times, setTimes] = useState([])
  const [startedAt, setStartedAt] = useState('')
  const [hotkey, setHotkey] = useState('Alt+L')
  const descRef = useRef(null)

  const refresh = useCallback(async () => {
    const [projs, active, cfg] = await Promise.all([
      window.api.getProjects(),
      window.api.getActive(),
      window.api.getConfig(),
    ])
    setProjects(projs)
    setTasks(projs[0]?.tasks || [])
    setActiveEntry(active)
    setHotkey(cfg.HOTKEY || 'Alt+L')
    const opts = timeOptions()
    setTimes(opts)
    setStartedAt(opts[0]?.value || '')
    setDesc('')
    setTimeout(() => descRef.current?.focus(), 50)
  }, [])

  useEffect(() => {
    refresh()
    const off = window.api.on('refresh', refresh)
    const onKey = (e) => {
      if (e.key === 'Escape') window.close?.()
      if (e.key === 'Enter' && document.activeElement === descRef.current) onLog()
    }
    window.addEventListener('keydown', onKey)
    return () => { off?.(); window.removeEventListener('keydown', onKey) }
  }, [refresh])

  const onProjChange = (idx) => {
    setSelectedProj(idx)
    setTasks(projects[idx]?.tasks || [])
    setSelectedTask(0)
  }

  const onEndTask = async () => {
    const now = new Date()
    const t = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`
    await window.api.endCurrent(t)
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

  return (
    <div style={{ padding: 0 }}>
      <div className="card" style={{ width: 420 }}>
        {/* Header */}
        <div className="card-header drag">
          <span className="label-xs" style={{ flex: 1 }}>WORKPULSE · QUICK LOG</span>
          <span style={{ fontSize: 10, color: 'var(--t3)', fontFamily: 'monospace' }}>{hotkey}</span>
        </div>

        <div style={{ padding: '14px 14px 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Running task */}
          {activeEntry && (
            <div>
              <div className="label-xs" style={{ marginBottom: 6 }}>NOW RUNNING</div>
              <div className="chip" style={{ marginBottom: 8 }}>
                <span style={{ color: '#4ade80', fontSize: 8 }}>●</span>
                <span style={{ flex: 1, fontSize: 11, color: 'var(--t1)' }}>
                  {activeEntry.task?.includes(' — ') ? activeEntry.task.split(' — ').slice(1).join(' — ') : activeEntry.task}
                </span>
                <span style={{ fontSize: 10, color: 'var(--t3)' }}>{elapsed(activeEntry.start_time)}</span>
              </div>
              <button className="btn btn-red no-drag" style={{ width: '100%' }} onClick={onEndTask}>
                ⏹  End Current Task
              </button>
            </div>
          )}

          <div className="label-xs">LOG NEW TASK</div>
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
            <span style={{ fontSize: 10, color: 'var(--t3)' }}>Started at:</span>
            <div style={{ flex: 1 }} />
            <select className="select no-drag" value={startedAt} onChange={e => setStartedAt(e.target.value)} style={{ width: 130 }}>
              {times.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-primary no-drag" style={{ flex: 1 }} onClick={onLog}>Log It</button>
            <button className="btn btn-ghost no-drag" style={{ width: 60 }} onClick={() => window.close?.()}>Esc</button>
          </div>
        </div>
      </div>
    </div>
  )
}
