import React, { useState, useEffect, useRef, useCallback } from 'react'

const STATE_STYLE = {
  active:  { dot: '#4ade80', bg: 'rgba(8,14,8,0.94)',  border: 'rgba(50,80,50,0.7)' },
  overdue: { dot: '#ef4444', bg: 'rgba(18,5,5,0.95)',  border: 'rgba(90,20,20,0.8)' },
  idle:    { dot: '#3d3b37', bg: 'rgba(10,10,10,0.88)', border: 'rgba(40,40,40,0.6)' },
}

function elapsed(startTime) {
  if (!startTime) return ''
  const now = new Date()
  const [h, m] = startTime.split(':').map(Number)
  const start = new Date(now); start.setHours(h, m, 0, 0)
  const mins = Math.max(0, Math.floor((now - start) / 60000))
  return mins < 60 ? `${mins}m` : `${Math.floor(mins/60)}h ${mins%60}m`
}

export default function StatusBar() {
  const [state, setState] = useState('idle')
  const [expanded, setExpanded] = useState(false)
  const [task, setTask] = useState('')
  const [elapsedStr, setElapsedStr] = useState('')
  const [activeEntry, setActiveEntry] = useState(null)
  const collapseTimer = useRef(null)
  const dotPhase = useRef(true)
  const [dotVisible, setDotVisible] = useState(true)

  const refresh = useCallback(async () => {
    const entry = await window.api.getActive()
    setActiveEntry(entry)
    if (entry) {
      let t = entry.task || ''
      if (t.includes(' — ')) t = t.split(' — ').slice(1).join(' — ')
      setTask(t.length > 40 ? t.slice(0, 40) + '…' : t)
      setElapsedStr(elapsed(entry.start_time))
    } else {
      setTask('')
      setElapsedStr('')
    }
  }, [])

  useEffect(() => {
    refresh()

    const off1 = window.api.on('state', (s) => setState(s))
    const off2 = window.api.on('refresh', refresh)

    const elapsedInt = setInterval(() => {
      if (activeEntry) setElapsedStr(elapsed(activeEntry.start_time))
    }, 60000)

    const dotInt = setInterval(() => {
      if (state !== 'idle') {
        dotPhase.current = !dotPhase.current
        setDotVisible(dotPhase.current)
      } else {
        setDotVisible(true)
      }
    }, 1500)

    return () => { off1?.(); off2?.(); clearInterval(elapsedInt); clearInterval(dotInt) }
  }, [refresh, activeEntry, state])

  const s = STATE_STYLE[state] || STATE_STYLE.idle

  const expand = () => {
    clearTimeout(collapseTimer.current)
    window.api.statusBarInteractive?.()
    setExpanded(true)
    refresh()
  }
  const scheduleCollapse = () => {
    collapseTimer.current = setTimeout(() => {
      setExpanded(false)
      window.api.statusBarPassthrough?.()
    }, 1500)
  }

  return (
    <div
      style={{ padding: '8px 20px', display: 'flex', justifyContent: 'center' }}
      onMouseEnter={expand}
      onMouseLeave={scheduleCollapse}
    >
      <div
        className="drag"
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: s.bg,
          border: `1px solid ${s.border}`,
          borderRadius: 999,
          padding: expanded ? '4px 12px' : '6px 8px',
          height: expanded ? 28 : 24,
          transition: 'all 0.2s ease',
          boxShadow: '0 2px 12px rgba(0,0,0,0.5)',
          overflow: 'hidden',
          whiteSpace: 'nowrap',
        }}
      >
        {/* Dot */}
        <span style={{
          width: 7, height: 7, borderRadius: '50%',
          background: s.dot,
          opacity: dotVisible ? 1 : 0.25,
          flexShrink: 0,
          transition: 'opacity 0.4s',
        }} />

        {expanded && task && (
          <>
            <span style={{ color: '#f2ede4', fontSize: 11, fontFamily: 'Sora, Segoe UI, sans-serif' }}>
              {task}
            </span>
            {elapsedStr && (
              <span style={{ color: 'rgba(233,187,81,0.6)', fontSize: 10, fontFamily: 'monospace', marginLeft: 4 }}>
                {elapsedStr}
              </span>
            )}
            {state === 'active' && activeEntry && (
              <button
                className="no-drag"
                onClick={() => window.api.on('open-interrupt', () => {})}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, color: '#e9bb51', padding: '0 2px', lineHeight: 1 }}
                title="Quick interrupt"
              >⚡</button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
