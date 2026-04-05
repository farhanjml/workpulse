import React, { useState, useEffect, useRef, useCallback } from 'react'

function Section({ label }) {
  return <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: 2.5, color: 'var(--t3)', textTransform: 'uppercase', padding: '4px 0' }}>{label}</div>
}

function Row({ label, children }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', background: 'var(--s2)', borderRadius: 8, padding: '8px 12px', gap: 8 }}>
      <span style={{ flex: 1, fontSize: 12, color: 'var(--t2)' }}>{label}</span>
      {children}
    </div>
  )
}

function Toggle({ checked, onChange }) {
  return (
    <div
      onClick={() => onChange(!checked)}
      style={{
        width: 36, height: 20, borderRadius: 10, cursor: 'pointer', flexShrink: 0,
        background: checked ? 'var(--gold)' : 'var(--s3)',
        border: `1px solid ${checked ? 'var(--gold)' : 'var(--border)'}`,
        position: 'relative', transition: 'background 0.2s',
      }}
    >
      <div style={{
        position: 'absolute', top: 2, left: checked ? 16 : 2,
        width: 14, height: 14, borderRadius: '50%',
        background: checked ? '#030404' : 'var(--t3)',
        transition: 'left 0.2s',
      }} />
    </div>
  )
}

function Slider({ value, min, max, suffix, onChange }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <input
        type="range" min={min} max={max} value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{ width: 100, accentColor: 'var(--gold)', cursor: 'pointer' }}
      />
      <span style={{ fontSize: 11, color: 'var(--gold)', width: 36, textAlign: 'right', fontFamily: 'monospace' }}>
        {value}{suffix}
      </span>
    </div>
  )
}

function HotkeyCapture({ value, onChange }) {
  const [recording, setRecording] = useState(false)
  const btnRef = useRef(null)

  const display = value?.replace(/\+/g, ' + ') || 'Click to set'

  const onKeyDown = useCallback((e) => {
    if (!recording) return
    e.preventDefault()
    const parts = []
    if (e.ctrlKey) parts.push('Ctrl')
    if (e.shiftKey) parts.push('Shift')
    if (e.altKey) parts.push('Alt')
    if (e.metaKey) parts.push('Meta')
    const ignored = ['Control','Shift','Alt','Meta']
    if (!ignored.includes(e.key) && parts.length >= 1) {
      const key = e.key.length === 1 ? e.key.toUpperCase() : e.key
      parts.push(key)
      onChange(parts.join('+'))
      setRecording(false)
    }
  }, [recording, onChange])

  useEffect(() => {
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onKeyDown])

  return (
    <button
      ref={btnRef}
      className="btn no-drag"
      style={{
        width: 180, fontSize: 11,
        background: recording ? 'var(--gold-bg)' : 'var(--s2)',
        borderColor: recording ? 'var(--gold-border)' : 'var(--border)',
        color: recording ? 'var(--gold)' : 'var(--t1)',
      }}
      onClick={() => setRecording(true)}
    >
      {recording ? 'Press keys…' : display}
    </button>
  )
}

export default function Settings() {
  const [cfg, setCfg] = useState(null)
  const [syncStatus, setSyncStatus] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    window.api.getConfig().then(c => {
      setCfg(c)
      setSyncStatus(c.LAST_CLOCKIFY_SYNC ? `Last synced: ${c.LAST_CLOCKIFY_SYNC}` : 'Not synced yet')
    })
  }, [])

  const update = (key, val) => setCfg(c => ({ ...c, [key]: val }))

  const onSave = async () => {
    await window.api.saveConfig(cfg)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    // Update theme immediately
    document.documentElement.setAttribute('data-theme', cfg.DARK_MODE ? 'dark' : 'light')
  }

  const onSync = async () => {
    setSyncStatus('Syncing…')
    // Pass current (possibly unsaved) credentials so sync works without hitting Save first
    const ok = await window.api.syncProjects({
      CLOCKIFY_API_KEY: cfg.CLOCKIFY_API_KEY,
      CLOCKIFY_WORKSPACE_ID: cfg.CLOCKIFY_WORKSPACE_ID,
    })
    if (ok) {
      const c = await window.api.getConfig()
      setSyncStatus(`Last synced: ${c.LAST_CLOCKIFY_SYNC}`)
    } else {
      setSyncStatus('Sync failed — check API key + Workspace ID')
    }
  }

  if (!cfg) return <div style={{ background: 'var(--bg)', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--t3)' }}>Loading…</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)', color: 'var(--t1)' }}>
      {/* Header */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)', background: 'var(--s1)' }}>
        <span style={{ fontSize: 14, fontWeight: 600 }}>Settings</span>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>

        <Section label="TIMING" />
        <Row label="Ping interval"><Slider value={cfg.PING_INTERVAL} min={1} max={15} suffix="m" onChange={v => update('PING_INTERVAL', v)} /></Row>
        <Row label="Idle threshold"><Slider value={cfg.IDLE_THRESHOLD} min={5} max={30} suffix="m" onChange={v => update('IDLE_THRESHOLD', v)} /></Row>
        <Row label="Overdue warning"><Slider value={cfg.OVERDUE_WARNING} min={20} max={90} suffix="m" onChange={v => update('OVERDUE_WARNING', v)} /></Row>
        <Row label="Status bar duration"><Slider value={cfg.STATUS_BAR_DURATION} min={3} max={30} suffix="s" onChange={v => update('STATUS_BAR_DURATION', v)} /></Row>
        <Row label="Work start">
          <input type="time" value={cfg.WORK_START} onChange={e => update('WORK_START', e.target.value)} className="input no-drag" style={{ width: 90 }} />
        </Row>
        <Row label="End of day">
          <input type="time" value={cfg.END_OF_DAY} onChange={e => update('END_OF_DAY', e.target.value)} className="input no-drag" style={{ width: 90 }} />
        </Row>

        <Section label="HOTKEYS" />
        <Row label="Quick log"><HotkeyCapture value={cfg.HOTKEY} onChange={v => update('HOTKEY', v)} /></Row>
        <Row label="Quick interrupt"><HotkeyCapture value={cfg.INTERRUPT_HOTKEY} onChange={v => update('INTERRUPT_HOTKEY', v)} /></Row>
        <div style={{ fontSize: 10, color: 'var(--t3)', padding: '0 4px' }}>Click a button, then press your desired key combo</div>

        <Section label="BEHAVIOUR" />
        <Row label="Start on boot"><Toggle checked={cfg.START_ON_BOOT} onChange={v => update('START_ON_BOOT', v)} /></Row>
        <Row label="Dark mode"><Toggle checked={cfg.DARK_MODE} onChange={v => update('DARK_MODE', v)} /></Row>
        <Row label="Clipboard hints"><Toggle checked={cfg.CLIPBOARD_HINTS} onChange={v => update('CLIPBOARD_HINTS', v)} /></Row>

        <Section label="SOUND" />
        <Row label="Sound theme">
          <select className="select no-drag" value={cfg.SOUND_THEME} onChange={e => update('SOUND_THEME', e.target.value)} style={{ width: 150 }}>
            <option value="soft_chime">Soft chime</option>
            <option value="typewriter">Typewriter ding</option>
            <option value="retro">Retro beep</option>
            <option value="none">None</option>
          </select>
        </Row>
        <Row label="Volume"><Slider value={cfg.VOLUME} min={0} max={100} suffix="%" onChange={v => update('VOLUME', v)} /></Row>
        <Row label="Play on">
          <select className="select no-drag" value={cfg.PLAY_ON} onChange={e => update('PLAY_ON', e.target.value)} style={{ width: 160 }}>
            <option value="all">All events</option>
            <option value="ping_only">Ping only</option>
            <option value="ping_overdue">Ping + Overdue</option>
            <option value="none">None</option>
          </select>
        </Row>

        <Section label="CLOCKIFY" />
        <Row label="API Key">
          <input type="password" className="input no-drag" style={{ width: 200 }} value={cfg.CLOCKIFY_API_KEY || ''} placeholder="Paste API key…" onChange={e => update('CLOCKIFY_API_KEY', e.target.value)} />
        </Row>
        <Row label="Workspace ID">
          <input type="text" className="input no-drag" style={{ width: 200 }} value={cfg.CLOCKIFY_WORKSPACE_ID || ''} placeholder="Workspace ID…" onChange={e => update('CLOCKIFY_WORKSPACE_ID', e.target.value)} />
        </Row>
        <Row label="Sync Projects">
          <button className="btn no-drag" style={{ background: 'var(--gold-bg)', borderColor: 'var(--gold-border)', color: 'var(--gold)' }} onClick={onSync}>↻ Sync</button>
        </Row>
        <div style={{ fontSize: 10, color: 'var(--t3)', padding: '0 4px' }}>{syncStatus}</div>
      </div>

      {/* Footer */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: '12px 16px', borderTop: '1px solid var(--border)', background: 'var(--s1)' }}>
        <button className="btn btn-ghost" onClick={() => window.close?.()}>Close</button>
        <button
          className="btn"
          style={saved
            ? { background: '#4ade80', borderColor: '#4ade80', color: '#0a2010', fontWeight: 700 }
            : { background: 'var(--gold)', borderColor: 'var(--gold)', color: '#030404', fontWeight: 700 }
          }
          onClick={onSave}
        >
          {saved ? 'Saved ✓' : 'Save'}
        </button>
      </div>
    </div>
  )
}
