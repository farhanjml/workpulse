import React, { useState, useEffect, useCallback } from 'react'

function fmt(mins) {
  if (mins < 60) return `${mins}m`
  return `${Math.floor(mins/60)}h ${mins%60}m`
}

function datePlus(dateStr, days) {
  const d = new Date(dateStr + 'T12:00:00')
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function duration(start, end) {
  if (!end) return null
  const [sh, sm] = start.split(':').map(Number)
  const [eh, em] = end.split(':').map(Number)
  return Math.max(0, (eh * 60 + em) - (sh * 60 + sm))
}

const PROJECT_COLORS = ['#e9bb51','#4ade80','#60a5fa','#f472b6','#a78bfa','#34d399','#fb923c']

export default function Summary() {
  const [date, setDate] = useState(todayStr())
  const [entries, setEntries] = useState([])
  const [total, setTotal] = useState(0)
  const [projects, setProjects] = useState([])

  const refresh = useCallback(async (d) => {
    const [ents, mins, projs] = await Promise.all([
      window.api.getEntries(d),
      window.api.totalMinutes(d),
      window.api.getProjects(),
    ])
    setEntries(ents)
    setTotal(mins)
    setProjects(projs)
  }, [])

  useEffect(() => {
    refresh(date)
    const off = window.api.on('refresh', () => refresh(date))
    return () => off?.()
  }, [date, refresh])

  const projColor = (projId) => {
    const idx = projects.findIndex(p => p.id === projId)
    return PROJECT_COLORS[idx % PROJECT_COLORS.length] || '#e9bb51'
  }

  const onDelete = async (id) => {
    await window.api.deleteEntry(id)
    refresh(date)
  }

  const onCopyAll = () => {
    const lines = entries.map(e =>
      `[${e.start_time}–${e.end_time || '...'}] ${e.project_name}: ${e.task}`
    ).join('\n')
    navigator.clipboard.writeText(lines)
  }

  // Gap detection
  const rows = []
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i]
    if (i > 0 && entries[i-1].end_time) {
      const [ph, pm] = entries[i-1].end_time.split(':').map(Number)
      const [ch, cm] = e.start_time.split(':').map(Number)
      const gap = (ch * 60 + cm) - (ph * 60 + pm)
      if (gap > 5) {
        rows.push({ type: 'gap', minutes: gap, key: `gap-${i}` })
      }
    }
    rows.push({ type: 'entry', entry: e, key: `e-${e.id}` })
  }

  const displayDate = date === todayStr() ? 'Today' : new Date(date + 'T12:00').toLocaleDateString('en-MY', { weekday: 'short', month: 'short', day: 'numeric' })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)', color: 'var(--t1)' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderBottom: '1px solid var(--border)', background: 'var(--s1)' }}>
        <button className="btn" style={{ padding: '5px 10px' }} onClick={() => setDate(d => datePlus(d, -1))}>‹</button>
        <span style={{ flex: 1, textAlign: 'center', fontWeight: 600, fontSize: 13 }}>{displayDate}</span>
        <button className="btn" style={{ padding: '5px 10px' }} onClick={() => setDate(d => datePlus(d, 1))}>›</button>
      </div>

      {/* Entry list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {rows.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--t3)', marginTop: 40, fontSize: 13 }}>No entries for this day</div>
        )}
        {rows.map(row => {
          if (row.type === 'gap') return (
            <div key={row.key} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 10px', borderRadius: 6, background: 'var(--red-bg)', border: '1px solid var(--red-border)' }}>
              <span style={{ color: 'var(--red)', fontSize: 10 }}>⚠</span>
              <span style={{ fontSize: 10, color: 'var(--red)' }}>{fmt(row.minutes)} gap</span>
            </div>
          )
          const e = row.entry
          const dur = duration(e.start_time, e.end_time)
          const taskLabel = e.task?.includes(' — ') ? e.task.split(' — ').slice(1).join(' — ') : e.task
          const taskType  = e.task?.includes(' — ') ? e.task.split(' — ')[0] : ''
          return (
            <div key={row.key} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderRadius: 8, background: 'var(--s1)', border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', minWidth: 80 }}>
                <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--t2)' }}>{e.start_time}</span>
                {e.end_time && <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--t3)' }}>{e.end_time}</span>}
              </div>
              <div style={{ width: 3, height: 32, borderRadius: 2, background: projColor(e.project_id), flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, color: 'var(--t1)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {taskLabel}
                </div>
                <div style={{ fontSize: 10, color: 'var(--t3)' }}>
                  {e.project_name}{taskType ? ` · ${taskType}` : ''}
                </div>
              </div>
              {dur !== null && <span style={{ fontSize: 11, color: 'var(--gold-dim)', fontFamily: 'monospace', flexShrink: 0 }}>{fmt(dur)}</span>}
              <button
                className="btn btn-ghost"
                style={{ padding: '3px 7px', fontSize: 11 }}
                onClick={() => navigator.clipboard.writeText(`${e.project_name}: ${e.task}`)}
                title="Copy"
              >⎘</button>
              <button
                className="btn btn-ghost"
                style={{ padding: '3px 7px', fontSize: 11, color: 'var(--red)' }}
                onClick={() => onDelete(e.id)}
                title="Delete"
              >✕</button>
            </div>
          )
        })}
      </div>

      {/* Footer */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderTop: '1px solid var(--border)', background: 'var(--s1)' }}>
        <span style={{ flex: 1, fontSize: 12, color: 'var(--t2)' }}>
          {entries.length} entries · <strong style={{ color: 'var(--gold)' }}>{fmt(total)}</strong> logged
        </span>
        <button className="btn" style={{ fontSize: 11, padding: '5px 10px' }} onClick={onCopyAll}>Copy All</button>
      </div>
    </div>
  )
}
