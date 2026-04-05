import React, { useState, useEffect, useRef, useCallback } from 'react'

const DURATIONS = [5, 10, 15, 30]

function elapsed(startTime) {
  if (!startTime) return ''
  const now = new Date()
  const [h, m] = startTime.split(':').map(Number)
  const start = new Date(now); start.setHours(h, m, 0, 0)
  const mins = Math.max(0, Math.floor((now - start) / 60000))
  return mins < 60 ? `${mins}m` : `${Math.floor(mins/60)}h ${mins%60}m`
}

export default function Interrupt() {
  const [projects, setProjects] = useState([])
  const [tasks, setTasks] = useState([])
  const [selectedProj, setSelectedProj] = useState(0)
  const [selectedTask, setSelectedTask] = useState(0)
  const [desc, setDesc] = useState('')
  const [duration, setDuration] = useState(10)
  const [activeEntry, setActiveEntry] = useState(null)
  const [hotkey, setHotkey] = useState('Alt+Shift+L')
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
    setHotkey(cfg.INTERRUPT_HOTKEY || 'Alt+Shift+L')
    setDesc('')
    setDuration(10)
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

  const onLog = async () => {
    if (!desc.trim()) { descRef.current?.focus(); return }
    const proj = projects[selectedProj]
    if (!proj) return
    const taskType = tasks[selectedTask] || ''
    const task = taskType ? `${taskType} — ${desc}` : desc
    await window.api.logInterrupt({ projectId: proj.id, projectName: proj.name, task, durationMinutes: duration })
    window.close?.()
  }

  return (
    <div style={{ padding: 0 }}>
      <div className="card" style={{ width: 380 }}>
        {/* Header */}
        <div className="card-header drag">
          <span style={{ color: '#e9bb51', fontSize: 8 }}>●</span>
          <span className="label-xs" style={{ flex: 1 }}>QUICK INTERRUPT</span>
          <span style={{ fontSize: 10, color: 'var(--t3)', fontFamily: 'monospace' }}>{hotkey}</span>
        </div>

        <div style={{ padding: '13px 14px 14px', display: 'flex', flexDirection: 'column', gap: 9 }}>
          {/* Running task chip */}
          <div className="chip">
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--t1)' }}>
                {activeEntry
                  ? (activeEntry.task?.includes(' — ') ? activeEntry.task.split(' — ').slice(1).join(' — ') : activeEntry.task)
                  : 'No active task'}
              </div>
              {activeEntry && (
                <div style={{ fontSize: 10, color: 'var(--t3)' }}>
                  {activeEntry.project_name} · {elapsed(activeEntry.start_time)}
                </div>
              )}
            </div>
            <span style={{
              fontSize: 9, fontWeight: 700,
              color: activeEntry ? '#4ade80' : 'var(--t3)',
              whiteSpace: 'nowrap',
            }}>
              {activeEntry ? '● still running' : '○ no task'}
            </span>
          </div>

          {/* Description */}
          <input ref={descRef} className="input no-drag" placeholder="Quick task description..." value={desc} onChange={e => setDesc(e.target.value)} autoFocus />

          {/* Project + task */}
          <div style={{ display: 'flex', gap: 8 }}>
            <select className="select no-drag" style={{ flex: 3 }} value={selectedProj} onChange={e => onProjChange(Number(e.target.value))}>
              {projects.map((p, i) => <option key={p.id} value={i}>{p.name}</option>)}
            </select>
            {tasks.length > 0 && (
              <select className="select no-drag" style={{ flex: 2 }} value={selectedTask} onChange={e => setSelectedTask(Number(e.target.value))}>
                {tasks.map((t, i) => <option key={i} value={i}>{t}</option>)}
              </select>
            )}
          </div>

          {/* Duration pills */}
          <div>
            <div className="label-xs" style={{ marginBottom: 6 }}>HOW LONG?</div>
            <div style={{ display: 'flex', gap: 6 }}>
              {DURATIONS.map(d => (
                <button
                  key={d}
                  className="no-drag"
                  onClick={() => setDuration(d)}
                  style={{
                    flex: 1, padding: '6px 0', borderRadius: 7, fontSize: 11, fontWeight: 600,
                    cursor: 'pointer', fontFamily: 'inherit',
                    background: d === duration ? 'var(--gold-bg)' : 'var(--s2)',
                    border: `1px solid ${d === duration ? 'var(--gold-border)' : 'var(--border)'}`,
                    color: d === duration ? 'var(--gold)' : 'var(--t2)',
                    transition: 'all 0.1s',
                  }}
                >{d}m</button>
              ))}
            </div>
          </div>

          {/* CTA */}
          <button className="btn btn-primary no-drag" onClick={onLog}>⚡  Quick Log</button>

          {/* Footer */}
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 9.5, color: 'var(--t3)' }}>Enter to log · Esc to cancel</span>
            <span style={{ fontSize: 9.5, color: 'var(--t3)' }}>main task keeps running</span>
          </div>
        </div>
      </div>
    </div>
  )
}
